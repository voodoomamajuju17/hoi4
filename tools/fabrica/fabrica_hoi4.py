# -*- coding: utf-8 -*-
"""Fábrica HOI4: ASSET_REQUEST -> PNG revisados + hoja de contacto + ZIP.

Versión 2 (2026-11-06), sobre la que armó ChatGPT para el usuario. Cambios:
  - lee también `material:` (los pines sin material pierden todo el estilo) y
    `reference_image:` (el ícono viejo / el original del juego), que se adjunta
    a la API como referencia del MOTIVO cuando está en la carpeta del TXT;
  - guarda la imagen grande, no achicada a 95x85: el mod la achica al importar
    y, si hay que retocarla, se parte de la grande (opción para achicar igual);
  - control de calidad en cada imagen (tools/fabrica/control.py): archivo que no
    abre, fondo blanco donde se pidió transparente (se intenta quitar solo),
    dibujo cortado contra el borde, casi vacía, plana. Lo que falla va a la
    subcarpeta `revisar/` y, si está marcado, se pide UNA vez más;
  - corta la tanda si fallan 5 pedidos seguidos (no gastar en un error repetido);
  - al terminar: hoja_de_contacto.jpg (lo que falló, con marco rojo) y
    control.csv con cada problema;
  - si la API no acepta un parámetro (por ejemplo `complexity`), lo saca y sigue.

Uso: doble clic en INICIAR.bat. Python 3.10+; pip install openai pillow.
La clave de API se escribe en la ventana o se toma de OPENAI_API_KEY; no se guarda.
"""
import base64
import csv
import io
import os
import queue
import re
import sys
import threading
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import control  # noqa: E402  (mismo directorio)

MAX_ZIP_BYTES = 29 * 1024 * 1024
MODELOS = ["gpt-image-2.6-sunburst", "gpt-image-2.6-flare", "gpt-image-2.5-sunburst", "gpt-image-1.5", "gpt-image-1"]
CAMPOS = ("type", "id", "filename", "size", "style", "material", "description", "reference_image",
          "transparent_background")
FALLAS_SEGUIDAS_MAX = 5


# -- pedidos -------------------------------------------------------------------

def leer_pedidos(texto: str, carpeta_txt: Path | None = None) -> list[dict]:
    """Los bloques ASSET_REQUEST del TXT, validados (sin gastar nada)."""
    inicios = list(re.finditer(r"(?m)^\s*ASSET_REQUEST\s*$", texto))
    if not inicios:
        raise ValueError("El TXT no tiene líneas ASSET_REQUEST.")
    pedidos = []
    for i, m in enumerate(inicios):
        fin = inicios[i + 1].start() if i + 1 < len(inicios) else len(texto)
        campos = {}
        for linea in texto[m.end():fin].splitlines():
            c = re.match(r"^\s*(" + "|".join(CAMPOS) + r")\s*:\s*(.*?)\s*$", linea, re.I)
            if c:
                campos[c.group(1).lower()] = c.group(2)
        nombre = campos.get("filename", "").strip().strip("`\"'")
        if not nombre:
            raise ValueError(f"Pedido {i + 1}: falta filename:")
        if Path(nombre).name != nombre or not nombre.lower().endswith(".png"):
            raise ValueError(f"Pedido {i + 1}: nombre inseguro o que no es PNG: {nombre}")
        t = re.search(r"(\d{2,5})\s*[x×]\s*(\d{2,5})", campos.get("size", "1024x1024"))
        if not t:
            raise ValueError(f"Pedido {i + 1} ({nombre}): tamaño no reconocido")
        w, h = map(int, t.groups())
        ref = None
        if campos.get("reference_image"):
            rel = campos["reference_image"].split(" (", 1)[0].strip()
            if carpeta_txt is not None:
                cand = (carpeta_txt / rel).resolve()
                # la referencia tiene que estar dentro de la carpeta del TXT
                if carpeta_txt.resolve() in cand.parents and cand.is_file():
                    ref = cand
        transp = campos.get("transparent_background", "false").strip().lower() in ("true", "yes", "1", "si", "sí")
        pedidos.append({**campos, "filename": nombre, "size": (w, h), "referencia": ref,
                        "referencia_pedida": bool(campos.get("reference_image")), "transparente": transp})
    nombres = [p["filename"].lower() for p in pedidos]
    repetidos = sorted({n for n in nombres if nombres.count(n) > 1})
    if repetidos:
        raise ValueError("Filenames repetidos: " + ", ".join(repetidos[:5]))
    return pedidos


def armar_prompt(p: dict) -> str:
    w, h = p["size"]
    partes = [
        "Create exactly ONE finished game art asset.",
        f"Asset type: {p.get('type', 'game asset')}.",
        f"Art direction / style: {p.get('style', '')}",
    ]
    if p.get("material"):
        partes.append(f"MATERIAL (mandatory, the object is made of exactly this): {p['material']}")
    partes += [
        f"Subject: {p.get('description', '')}",
        f"It will be shown at {w}x{h} pixels: compose for that aspect ratio, big simple shapes, readable that small.",
        "The whole subject must be inside the frame with a small margin: nothing cut by the edges.",
        "No words, letters, numbers or watermarks unless the description asks for an exact text.",
        "One single image: no contact sheet, no alternatives, no mockup, no frame around it.",
    ]
    if p.get("type") == "national_focus_icon":
        partes.append("It is a PIN, not a coin or a medal: the outline follows the emblem; no ring of extra symbols.")
    if p["transparente"]:
        partes.append("Truly transparent background (alpha). No white or grey backing, no floor, no table.")
    if p.get("referencia"):
        partes.append("The attached image is ONLY a reference for WHAT to depict (the subject). Ignore its style, "
                      "colours, frame and background: redraw it completely in the art direction and material above.")
    return "\n".join(partes)


def tamano_api(w: int, h: int) -> str:
    """Proporción del pedido, lado mayor ~1024, múltiplos de 16."""
    k = 1024 / max(w, h)
    return f"{max(256, round(w * k / 16) * 16)}x{max(256, round(h * k / 16) * 16)}"


def ajustar(img, size, transparente):
    from PIL import Image, ImageOps
    if transparente:
        dentro = ImageOps.contain(img, size, method=Image.Resampling.LANCZOS)
        lienzo = Image.new("RGBA", size, (0, 0, 0, 0))
        lienzo.alpha_composite(dentro, ((size[0] - dentro.width) // 2, (size[1] - dentro.height) // 2))
        return lienzo
    return ImageOps.fit(img, size, method=Image.Resampling.LANCZOS)


# -- la API ---------------------------------------------------------------------

class Generador:
    """Llama a la API. Si un parámetro opcional es rechazado, lo saca y lo recuerda."""

    OPCIONALES = ("complexity", "output_format", "background", "quality", "size")

    def __init__(self, client, model, quality, complexity, log):
        self.client, self.model, self.log = client, model, log
        self.base = {"quality": quality, "output_format": "png"}
        if complexity:
            self.base["complexity"] = complexity
        self.sacados: set[str] = set()
        self.sin_referencias = False

    def _params(self, p, prompt):
        d = {"model": self.model, "prompt": prompt, "n": 1, **self.base,
             "size": tamano_api(*p["size"]), "background": "transparent" if p["transparente"] else "opaque"}
        for k in self.sacados:
            d.pop(k, None)
        return d

    def generar(self, p) -> bytes:
        from openai import BadRequestError
        usar_ref = p.get("referencia") is not None and not self.sin_referencias
        prompt = armar_prompt(p if usar_ref else {**p, "referencia": None})
        while True:
            d = self._params(p, prompt)
            try:
                if usar_ref:
                    with open(p["referencia"], "rb") as f:
                        r = self.client.images.edit(image=f, **d)
                else:
                    r = self.client.images.generate(**d)
                return base64.b64decode(r.data[0].b64_json)
            except BadRequestError as ex:
                texto = str(ex).lower()
                culpable = next((k for k in self.OPCIONALES if k in texto and k in d), None)
                if culpable:
                    self.sacados.add(culpable)
                    self.log(f"  la API no acepta '{culpable}': lo saco y sigo")
                    continue
                if usar_ref:
                    self.sin_referencias = True
                    usar_ref = False
                    prompt = armar_prompt({**p, "referencia": None})
                    self.log("  la API no acepta la imagen de referencia: sigo sin referencias")
                    continue
                raise


def procesar(p, datos: bytes, carpeta: Path, achicar: bool) -> list[str]:
    """Revisa, quita el fondo si hace falta y guarda. Devuelve los problemas."""
    img = control.abrir(datos)
    if img is None:
        return ["la API devolvió algo que no abre"]
    notas = []
    if p["transparente"]:
        img, quitado = control.quitar_fondo(img)
        if quitado:
            notas.append("fondo quitado")
    problemas = control.revisar(img, p["transparente"])
    if achicar:
        img = ajustar(img, p["size"], p["transparente"])
    destino = (carpeta / "revisar" if problemas else carpeta) / p["filename"]
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(destino.stem + ".tmp.png")
    img.save(tmp, format="PNG", optimize=True)
    if control.abrir(tmp) is None:   # verificar lo escrito
        tmp.unlink(missing_ok=True)
        return ["no se pudo escribir bien el PNG"]
    tmp.replace(destino)
    if not problemas:
        (carpeta / "revisar" / p["filename"]).unlink(missing_ok=True)
    return problemas + ([f"({', '.join(notas)})"] if notas and not problemas else [])


def zips(carpeta: Path) -> list[Path]:
    archivos = sorted(carpeta.glob("*.png"))
    partes, actual, total = [], [], 0
    for f in archivos:
        t = f.stat().st_size + 200
        if actual and total + t > MAX_ZIP_BYTES:
            partes.append(actual)
            actual, total = [], 0
        actual.append(f)
        total += t
    if actual:
        partes.append(actual)
    salida = []
    for n, parte in enumerate(partes, 1):
        z = carpeta / f"ZIP_parte_{n:02}.zip"
        with zipfile.ZipFile(z, "w", compression=zipfile.ZIP_STORED) as zz:
            for f in parte:
                zz.write(f, arcname=f.name)
        salida.append(z)
    return salida


def tanda(pedidos, carpeta: Path, generador, log, parar, progreso, achicar=False, omitir=True, reintentar=True):
    """Genera, revisa y guarda. Sin interfaz: se puede probar con un generador falso."""
    from openai import APIConnectionError, APITimeoutError, InternalServerError, RateLimitError
    carpeta.mkdir(parents=True, exist_ok=True)
    informe, hechos, fallas_seguidas = [], 0, 0
    for i, p in enumerate(pedidos, 1):
        if parar.is_set():
            log("Parado a pedido.")
            break
        nombre = p["filename"]
        if omitir and (carpeta / nombre).is_file() and control.abrir(carpeta / nombre) is not None:
            log(f"[{i}/{len(pedidos)}] ya está: {nombre}")
            progreso(i)
            continue
        if p["referencia_pedida"] and p.get("referencia") is None:
            log(f"  aviso: {nombre} pide una referencia que no está junto al TXT (extraé pedidos.zip entero)")
        intentos_calidad = 2 if reintentar else 1
        for intento in range(intentos_calidad):
            log(f"[{i}/{len(pedidos)}] {nombre}" + (" (otra vez, no pasó el control)" if intento else ""))
            datos, ultimo = None, None
            for espera in (0, 15, 40):
                if espera:
                    log(f"  error temporal; reintento en {espera} s")
                    if parar.wait(espera):
                        break
                try:
                    datos = generador.generar(p)
                    break
                except (RateLimitError, InternalServerError, APIConnectionError) as ex:
                    ultimo = ex
                except APITimeoutError:
                    log("  tiempo agotado: no reintento (podría cobrarse dos veces)")
                    break
                except Exception as ex:   # noqa: BLE001
                    log(f"  ERROR: {type(ex).__name__}: {ex}")
                    break
            else:
                log(f"  ERROR tras 3 intentos: {ultimo}")
            if datos is None:
                informe.append((nombre, "falló la API"))
                fallas_seguidas += 1
                break
            fallas_seguidas = 0
            problemas = procesar(p, datos, carpeta, achicar)
            reales = [x for x in problemas if not x.startswith("(")]
            if not reales:
                hechos += 1
                log(f"  OK {' '.join(problemas)}")
                informe.append((nombre, "ok " + " ".join(problemas)))
                break
            log(f"  NO PASÓ EL CONTROL: {'; '.join(reales)}")
            if intento == intentos_calidad - 1:
                informe.append((nombre, "; ".join(reales) + " -> en revisar/"))
        progreso(i)
        if fallas_seguidas >= FALLAS_SEGUIDAS_MAX:
            log(f"Paro: {FALLAS_SEGUIDAS_MAX} pedidos seguidos fallaron (revisá la clave, el modelo o el saldo).")
            break
    # informe, hoja de contacto y zips
    with open(carpeta / "control.csv", "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(informe)
    malos = {n: e for n, e in informe if not e.startswith("ok")}
    pngs = sorted(carpeta.glob("*.png")) + sorted((carpeta / "revisar").glob("*.png"))
    control.hoja_de_contacto([x for x in pngs if not x.name.startswith("hoja_")], carpeta / "hoja_de_contacto.jpg",
                             problemas=malos)
    log(f"FIN · nuevas bien: {hechos} · con problemas: {len(malos)} (en revisar/ y control.csv) · "
        f"mirá hoja_de_contacto.jpg antes de mandar")
    return hechos, malos


# -- la ventana -----------------------------------------------------------------

def main():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.title("Fábrica HOI4 · v2 con control de calidad")
    root.geometry("860x700")
    eventos: "queue.Queue" = queue.Queue()
    parar = threading.Event()
    v = {k: tk.StringVar() for k in ("txt", "dest", "first", "count")}
    v["first"].set("1")
    v["count"].set("1")
    clave = tk.StringVar(value=os.getenv("OPENAI_API_KEY", ""))
    modelo, calidad, complejidad = tk.StringVar(value=MODELOS[0]), tk.StringVar(value="medium"), tk.StringVar(value="medium")
    omitir, achicar, reintentar, hacer_zip = (tk.BooleanVar(value=x) for x in (True, False, True, True))

    f = ttk.Frame(root, padding=14)
    f.pack(fill="both", expand=True)
    ttk.Label(f, text="FÁBRICA DE ASSETS · HOI4", font=("Segoe UI", 17, "bold")).pack(anchor="w")
    ttk.Label(f, text="Extraé pedidos.zip ENTERO y elegí un TXT de adentro: así encuentra las referencias.").pack(anchor="w", pady=(0, 10))

    def fila(texto, var, cmd=None, oculto=False):
        r = ttk.Frame(f)
        r.pack(fill="x", pady=2)
        ttk.Label(r, text=texto, width=18).pack(side="left")
        ttk.Entry(r, textvariable=var, show="•" if oculto else "").pack(side="left", fill="x", expand=True)
        if cmd:
            ttk.Button(r, text="Buscar…", command=cmd).pack(side="left", padx=(6, 0))

    def elegir_txt():
        p = filedialog.askopenfilename(filetypes=[("Texto", "*.txt")])
        if p:
            v["txt"].set(p)
            if not v["dest"].get():
                v["dest"].set(str(Path(p).parent / (Path(p).stem + "_PNG")))

    fila("Archivo TXT", v["txt"], elegir_txt)
    fila("Carpeta de salida", v["dest"], lambda: v["dest"].set(filedialog.askdirectory() or v["dest"].get()))
    fila("API key", clave, oculto=True)
    s = ttk.Frame(f)
    s.pack(fill="x", pady=6)
    for col, (t, var, vals) in enumerate((("Modelo", modelo, MODELOS), ("Calidad", calidad, ["medium", "high", "low", "auto"]),
                                          ("Complejidad", complejidad, ["medium", "low", "high", ""]))):
        ttk.Label(s, text=t).grid(row=0, column=col, sticky="w")
        ttk.Combobox(s, textvariable=var, values=vals, state="readonly", width=24).grid(row=1, column=col, sticky="ew", padx=(0, 8))
    lim = ttk.Frame(f)
    lim.pack(fill="x", pady=4)
    ttk.Label(lim, text="Desde pedido Nº").pack(side="left")
    ttk.Entry(lim, textvariable=v["first"], width=6).pack(side="left", padx=(6, 14))
    ttk.Label(lim, text="Cantidad (0 = todos)").pack(side="left")
    ttk.Entry(lim, textvariable=v["count"], width=7).pack(side="left", padx=6)
    o = ttk.Frame(f)
    o.pack(fill="x", pady=4)
    for t, var in (("Omitir los que ya están", omitir), ("Pedir una vez más si no pasa el control", reintentar),
                   ("Achicar al tamaño exacto (no recomendado)", achicar), ("Crear ZIP", hacer_zip)):
        ttk.Checkbutton(o, text=t, variable=var).pack(side="left", padx=(0, 10))
    b = ttk.Frame(f)
    b.pack(fill="x", pady=6)
    barra = ttk.Progressbar(f, mode="determinate")
    texto = tk.Text(f, height=16, wrap="word", state="disabled", font=("Consolas", 9))

    def log(m):
        eventos.put(("log", m))

    def seleccion():
        p = Path(v["txt"].get().strip())
        if not p.is_file():
            raise ValueError("Elegí un TXT que exista.")
        todos = leer_pedidos(p.read_text(encoding="utf-8-sig"), p.parent)
        a, c = int(v["first"].get()), int(v["count"].get())
        sel = todos[a - 1: None if c == 0 else a - 1 + c]
        if not sel:
            raise ValueError("No hay pedidos en ese rango.")
        if not v["dest"].get().strip():
            raise ValueError("Elegí la carpeta de salida.")
        return todos, sel, Path(v["dest"].get().strip())

    def analizar():
        try:
            todos, sel, out = seleccion()
        except Exception as ex:   # noqa: BLE001
            messagebox.showerror("No se pudo leer", str(ex))
            return
        faltan = [p for p in sel if not (out / p["filename"]).is_file()]
        sin_ref = [p["filename"] for p in sel if p["referencia_pedida"] and p["referencia"] is None]
        log(f"{len(todos)} pedidos en el TXT; elegidos {len(sel)}; por hacer {len(faltan)}.")
        if sin_ref:
            log(f"AVISO: {len(sin_ref)} piden referencia y no la encuentro junto al TXT (ej. {sin_ref[0]}). "
                "Extraé pedidos.zip entero, sin mover el TXT.")
        log("Analizar no gasta nada.")

    def generar():
        try:
            _, sel, out = seleccion()
            k = clave.get().strip()
            if not k.startswith("sk-"):
                raise ValueError("Falta la API key (empieza con sk-).")
        except Exception as ex:   # noqa: BLE001
            messagebox.showerror("Revisá", str(ex))
            return
        n = sum(1 for p in sel if not (omitir.get() and (out / p["filename"]).is_file()))
        extra = " (hasta el doble si hay que repetir alguna)" if reintentar.get() else ""
        if not messagebox.askyesno("Confirmar", f"Vas a pedir {n} imágenes pagas{extra}.\nModelo {modelo.get()}, calidad {calidad.get()}.\n¿Empezar?"):
            return
        from openai import OpenAI
        gen = Generador(OpenAI(api_key=k, timeout=180.0, max_retries=0), modelo.get(), calidad.get(), complejidad.get(), log)
        parar.clear()
        barra.configure(maximum=len(sel), value=0)
        boton_gen.configure(state="disabled")

        def trabajo():
            try:
                tanda(sel, out, gen, log, parar, lambda i: eventos.put(("prog", i)), achicar.get(), omitir.get(), reintentar.get())
                if hacer_zip.get():
                    for z in zips(out):
                        log(f"ZIP: {z.name}")
            except Exception as ex:   # noqa: BLE001
                log(f"ERROR GENERAL: {type(ex).__name__}: {ex}")
            finally:
                eventos.put(("fin", None))

        threading.Thread(target=trabajo, daemon=True).start()

    ttk.Button(b, text="Analizar TXT (gratis)", command=analizar).pack(side="left")
    boton_gen = ttk.Button(b, text="GENERAR (cuesta)", command=generar)
    boton_gen.pack(side="left", padx=8)
    ttk.Button(b, text="Parar después de la actual", command=parar.set).pack(side="left")
    barra.pack(fill="x", pady=6)
    texto.pack(fill="both", expand=True)

    def mirar():
        try:
            while True:
                k, c = eventos.get_nowait()
                if k == "log":
                    texto.configure(state="normal")
                    texto.insert("end", c + "\n")
                    texto.see("end")
                    texto.configure(state="disabled")
                elif k == "prog":
                    barra.configure(value=c)
                elif k == "fin":
                    boton_gen.configure(state="normal")
        except queue.Empty:
            pass
        root.after(150, mirar)

    log("Primero: Analizar TXT. Probá con Cantidad 1 y mirá la hoja de contacto.")
    mirar()
    root.mainloop()


if __name__ == "__main__":
    main()
