# -*- coding: utf-8 -*-
"""Fábrica HOI4: ASSET_REQUEST -> PNG revisados + hoja de contacto + ZIP.

Versión 3 (2026-11-06). La base es la que armó ChatGPT; la v2 sumó material,
referencias y control de calidad; la v3 sigue la auditoría que ChatGPT le hizo
a la v2 ("la fábrica nunca debería intentar arreglar una imagen pagando otra
generación sin que vos lo autorices"):

  1. si la API rechaza una referencia, ESE pedido falla y se avisa; seguir sin
     referencia solo con la casilla marcada (y queda anotado). 3 rechazos
     seguidos paran la tanda;
  2. no se repite nada automáticamente (la casilla existe, apagada);
  3. el fondo no se quita en silencio: la limpieza va a revisar/ y el original
     queda intacto en masters/;
  4. tope de pedidos pagos y tope en dólares (con el precio por imagen que
     pongas); registro.csv anota cada llamada, con el uso que informe la API;
  5. masters/ (lo que devolvió la API, intacto), final/ (tamaño exacto para el
     juego), revisar/ (lo dudoso); los ZIP salen solo de final/;
  6. estado.json por imagen (huella del pedido y resultado): al retomar no se
     paga lo hecho, y si cambió el pedido se avisa. Los ZIP se rearman desde
     cero cada vez.

Uso: doble clic en INICIAR.bat. Python 3.10+; pip install openai pillow.
La clave de API se escribe en la ventana o se toma de OPENAI_API_KEY; no se guarda.
"""
import base64
import csv
import datetime
import hashlib
import io
import json
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
RECHAZOS_REF_MAX = 3


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


def huella(p: dict) -> str:
    """Identifica el pedido tal como está escrito: si cambia, la imagen vieja no corresponde."""
    clave = json.dumps({k: p.get(k) for k in CAMPOS}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(clave.encode("utf-8")).hexdigest()[:12]


# -- la API ---------------------------------------------------------------------

class ReferenciaRechazada(Exception):
    pass


class Generador:
    """Llama a la API. Si un parámetro opcional es rechazado, lo saca y lo recuerda.
    Devuelve (bytes, uso, con_referencia)."""

    OPCIONALES = ("complexity", "output_format", "background", "quality", "size")

    def __init__(self, client, model, quality, complexity, log, permitir_sin_ref=False):
        self.client, self.model, self.log = client, model, log
        self.base = {"quality": quality, "output_format": "png"}
        if complexity:
            self.base["complexity"] = complexity
        self.sacados: set[str] = set()
        self.permitir_sin_ref = permitir_sin_ref

    def _params(self, p, prompt):
        d = {"model": self.model, "prompt": prompt, "n": 1, **self.base,
             "size": tamano_api(*p["size"]), "background": "transparent" if p["transparente"] else "opaque"}
        for k in self.sacados:
            d.pop(k, None)
        return d

    def generar(self, p):
        from openai import BadRequestError
        usar_ref = p.get("referencia") is not None
        prompt = armar_prompt(p if usar_ref else {**p, "referencia": None})
        while True:
            d = self._params(p, prompt)
            try:
                if usar_ref:
                    with open(p["referencia"], "rb") as f:
                        r = self.client.images.edit(image=f, **d)
                else:
                    r = self.client.images.generate(**d)
                uso = getattr(r, "usage", None)
                uso = uso.model_dump() if hasattr(uso, "model_dump") else uso
                return base64.b64decode(r.data[0].b64_json), uso, usar_ref
            except BadRequestError as ex:
                texto = str(ex).lower()
                culpable = next((k for k in self.OPCIONALES if k in texto and k in d), None)
                if culpable:
                    self.sacados.add(culpable)
                    self.log(f"  la API no acepta '{culpable}': lo saco y sigo")
                    continue
                if usar_ref:
                    if not self.permitir_sin_ref:
                        # 2026-11-06 (auditoría, punto 1): no apagar las referencias en silencio
                        raise ReferenciaRechazada(str(ex)) from ex
                    self.log("  la API rechazó la referencia: ESTE pedido va sin referencia (casilla marcada)")
                    usar_ref = False
                    prompt = armar_prompt({**p, "referencia": None})
                    continue
                raise


# -- guardar ------------------------------------------------------------------------

def carpetas(base: Path) -> dict:
    c = {k: base / k for k in ("masters", "final", "revisar")}
    for d in c.values():
        d.mkdir(parents=True, exist_ok=True)
    return c


def _escribir(img, destino: Path) -> bool:
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(destino.stem + ".tmp.png")
    img.save(tmp, format="PNG", optimize=True)
    if control.abrir(tmp) is None:
        tmp.unlink(missing_ok=True)
        return False
    tmp.replace(destino)
    return True


def procesar(p, datos: bytes, base: Path) -> tuple[str, list[str]]:
    """Guarda el original intacto en masters/ y decide: final/ (listo) o revisar/.
    Devuelve (estado, problemas). Nunca pide otra imagen."""
    c = carpetas(base)
    nombre = p["filename"]
    img = control.abrir(datos)
    if img is None:
        return "falló", ["la API devolvió algo que no abre"]
    if not _escribir(img, c["masters"] / nombre):
        return "falló", ["no se pudo escribir bien el PNG"]
    problemas = []
    if p["transparente"]:
        limpio, quitado = control.quitar_fondo(img)
        if quitado:
            # 2026-11-06 (auditoría, punto 3): la limpieza no va directo al juego
            problemas.append("vino con fondo liso: se lo quité, revisá que no se haya comido parte del dibujo")
            img = limpio
    problemas += control.revisar(img, p["transparente"])
    if problemas:
        _escribir(img, c["revisar"] / nombre)
        (c["final"] / nombre).unlink(missing_ok=True)
        return "revisar", problemas
    if not _escribir(ajustar(img, p["size"], p["transparente"]), c["final"] / nombre):
        return "falló", ["no se pudo escribir bien el PNG"]
    (c["revisar"] / nombre).unlink(missing_ok=True)
    return "ok", []


def leer_estado(base: Path) -> dict:
    try:
        return json.loads((base / "estado.json").read_text(encoding="utf-8"))
    except Exception:   # noqa: BLE001
        return {}


def guardar_estado(base: Path, estado: dict) -> None:
    tmp = base / "estado.json.tmp"
    tmp.write_text(json.dumps(estado, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(base / "estado.json")


def registrar(base: Path, fila: list) -> None:
    nuevo = not (base / "registro.csv").exists()
    with open(base / "registro.csv", "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(["fecha", "archivo", "estado", "problemas", "modelo", "calidad", "con_referencia",
                        "huella", "uso_api", "pagas_en_la_corrida"])
        w.writerow(fila)


def ya_hecho(p, base: Path, estado: dict) -> str | None:
    """Motivo para no volver a pagarla, o None si hay que generarla."""
    nombre = p["filename"]
    final = base / "final" / nombre
    if final.is_file() and control.abrir(final) is not None:
        e = estado.get(nombre) or {}
        if e.get("huella") and e["huella"] != huella(p):
            return "está en final/, pero el pedido cambió desde entonces (borrala de final/ para rehacerla)"
        return "ya está en final/"
    if (base / "revisar" / nombre).is_file():
        return "está en revisar/: aprobala moviéndola a final/, o borrala para rehacerla"
    return None


def zips(base: Path, pedidos: list | None = None) -> list[Path]:
    """ZIP desde cero, solo con final/; lo aprobado a mano desde revisar/ se lleva al tamaño exacto."""
    for viejo in base.glob("ZIP_parte_*.zip"):
        viejo.unlink()
    por_nombre = {p["filename"]: p for p in pedidos or []}
    archivos = []
    for f in sorted((base / "final").glob("*.png")):
        img = control.abrir(f)
        if img is None:
            continue
        p = por_nombre.get(f.name)
        if p and img.size != tuple(p["size"]):
            _escribir(ajustar(img, p["size"], p["transparente"]), f)
        archivos.append(f)
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
        z = base / f"ZIP_parte_{n:02}.zip"
        with zipfile.ZipFile(z, "w", compression=zipfile.ZIP_STORED) as zz:
            for f in parte:
                zz.write(f, arcname=f.name)
        salida.append(z)
    return salida


def tanda(pedidos, base: Path, generador, log, parar, progreso, tope_pagas=0, precio=0.0, tope_usd=0.0,
          reintentar=False, modelo="", calidad=""):
    """Genera, revisa y guarda. Sin interfaz: se puede probar con un generador falso.
    tope_pagas / tope_usd en 0 = sin tope (la ventana siempre pone uno)."""
    from openai import APIConnectionError, APITimeoutError, InternalServerError, RateLimitError
    carpetas(base)
    estado = leer_estado(base)
    pagas, hechos, fallas_seguidas, rechazos_seguidos = 0, 0, 0, 0
    malos: dict = {}

    def puede_pagar():
        if tope_pagas and pagas >= tope_pagas:
            log(f"Paro: llegué al tope de {tope_pagas} pedidos pagos.")
            return False
        if tope_usd and precio and (pagas + 1) * precio > tope_usd + 1e-9:
            log(f"Paro: la próxima pasaría el tope de USD {tope_usd:.2f} (estimado {pagas * precio:.2f} gastado).")
            return False
        return True

    for i, p in enumerate(pedidos, 1):
        if parar.is_set():
            log("Parado a pedido.")
            break
        nombre = p["filename"]
        motivo = ya_hecho(p, base, estado)
        if motivo:
            log(f"[{i}/{len(pedidos)}] {nombre}: {motivo}")
            progreso(i)
            continue
        if p["referencia_pedida"] and p.get("referencia") is None:
            log(f"  aviso: {nombre} pide una referencia que no está junto al TXT (extraé pedidos.zip entero)")
        for intento in range(2 if reintentar else 1):
            if not puede_pagar():
                parar.set()
                break
            log(f"[{i}/{len(pedidos)}] {nombre}" + (" (otra vez: no pasó el control)" if intento else ""))
            datos, uso, con_ref, error = None, None, False, ""
            for espera in (0, 15, 40):
                if espera:
                    log(f"  error temporal; reintento en {espera} s (estos no se cobran)")
                    if parar.wait(espera):
                        break
                try:
                    datos, uso, con_ref = generador.generar(p)
                    break
                except ReferenciaRechazada as ex:
                    error = f"la API rechazó la referencia ({ex})"
                    rechazos_seguidos += 1
                    break
                except (RateLimitError, InternalServerError, APIConnectionError) as ex:
                    error = f"{type(ex).__name__}: {ex}"
                except APITimeoutError:
                    # puede haberse cobrado: cuenta para el tope
                    pagas += 1
                    error = "tiempo agotado (no reintento: podría cobrarse dos veces)"
                    break
                except Exception as ex:   # noqa: BLE001
                    error = f"{type(ex).__name__}: {ex}"
                    break
            if datos is None:
                log(f"  FALLÓ: {error}")
                malos[nombre] = error
                registrar(base, [datetime.datetime.now().isoformat(timespec="seconds"), nombre, "falló", error,
                                 modelo, calidad, "", huella(p), "", pagas])
                fallas_seguidas += 1
                break
            pagas += 1
            fallas_seguidas = 0
            if con_ref or not p.get("referencia"):
                rechazos_seguidos = 0
            res, problemas = procesar(p, datos, base)
            estado[nombre] = {"huella": huella(p), "estado": res, "problemas": problemas,
                              "con_referencia": con_ref}
            guardar_estado(base, estado)
            registrar(base, [datetime.datetime.now().isoformat(timespec="seconds"), nombre, res, "; ".join(problemas),
                             modelo, calidad, "sí" if con_ref else ("NO" if p.get("referencia") else ""),
                             huella(p), json.dumps(uso) if uso else "", pagas])
            if res == "ok":
                hechos += 1
                malos.pop(nombre, None)
                log("  OK" + ("" if con_ref or not p.get("referencia") else " (SIN referencia)"))
                break
            log(f"  A REVISAR: {'; '.join(problemas)}")
            malos[nombre] = "; ".join(problemas)
        progreso(i)
        if fallas_seguidas >= FALLAS_SEGUIDAS_MAX:
            log(f"Paro: {FALLAS_SEGUIDAS_MAX} pedidos seguidos fallaron (revisá la clave, el modelo o el saldo).")
            break
        if rechazos_seguidos >= RECHAZOS_REF_MAX:
            log(f"Paro: la API rechazó {RECHAZOS_REF_MAX} referencias seguidas. Si querés seguir sin ellas, "
                "marcá 'Permitir sin referencia' (los pines pueden salir con otro motivo).")
            break
        if parar.is_set():
            break
    imgs = sorted((base / "final").glob("*.png")) + sorted((base / "revisar").glob("*.png"))
    control.hoja_de_contacto(imgs, base / "hoja_de_contacto.jpg",
                             problemas={n: e for n, e in malos.items()} | {x.name: "revisar" for x in (base / "revisar").glob("*.png")})
    estimado = f" · gasto estimado USD {pagas * precio:.2f}" if precio else ""
    log(f"FIN · pagas en esta corrida: {pagas}{estimado} · listas: {hechos} · para revisar o fallidas: {len(malos)} · "
        "mirá hoja_de_contacto.jpg")
    return hechos, malos, pagas


# -- la ventana -----------------------------------------------------------------

def main():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.title("Fábrica HOI4 · v3")
    root.geometry("980x800")
    eventos: "queue.Queue" = queue.Queue()
    parar = threading.Event()
    v = {k: tk.StringVar() for k in ("txt", "dest", "first", "count", "tope", "precio", "usd")}
    v["first"].set("1")
    v["count"].set("1")
    v["tope"].set("20")
    v["precio"].set("")
    v["usd"].set("")
    clave = tk.StringVar(value=os.getenv("OPENAI_API_KEY", ""))
    modelo, calidad, complejidad = tk.StringVar(value=MODELOS[0]), tk.StringVar(value="medium"), tk.StringVar(value="medium")
    reintentar, sin_ref, hacer_zip = (tk.BooleanVar(value=x) for x in (False, False, True))

    f = ttk.Frame(root, padding=14)
    f.pack(fill="both", expand=True)
    ttk.Label(f, text="FÁBRICA DE ASSETS · HOI4 · v3", font=("Segoe UI", 17, "bold")).pack(anchor="w")
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
    for t, k, w in (("Desde el pedido Nº", "first", 6), ("Cuántos pedidos (0 = todos)", "count", 6)):
        ttk.Label(lim, text=t).pack(side="left")
        ttk.Entry(lim, textvariable=v[k], width=w).pack(side="left", padx=(4, 14))
    # 2026-11-06 (captura: "no entiendo" el "Tope de pedidos PAGOS"): nombres más claros
    gasto = ttk.LabelFrame(f, text="Freno de gasto (sin al menos uno de los dos máximos no arranca)", padding=8)
    gasto.pack(fill="x", pady=4)
    for t, k, w in (("Máximo de imágenes a pagar en esta corrida", "tope", 6),
                    ("Precio de cada imagen (USD)", "precio", 7), ("Máximo a gastar (USD)", "usd", 7)):
        ttk.Label(gasto, text=t).pack(side="left")
        ttk.Entry(gasto, textvariable=v[k], width=w).pack(side="left", padx=(4, 14))
    ttk.Label(f, wraplength=840, justify="left",
              text="Ejemplo: máximo 20 imágenes → para al llegar a 20 aunque falten más; la próxima vez sigue donde quedó. "
                   "El precio de cada imagen lo ves en platform.openai.com/pricing (según modelo y calidad); "
                   "si lo ponés, también podés frenar por plata (ej. máximo USD 5). registro.csv anota cada llamada.").pack(anchor="w")
    o = ttk.Frame(f)
    o.pack(fill="x", pady=4)
    for t, var in (("Repetir automáticamente las que no pasen el control (cuesta)", reintentar),
                   ("Permitir sin referencia si la API la rechaza", sin_ref), ("Crear ZIP", hacer_zip)):
        ttk.Checkbutton(o, text=t, variable=var).pack(side="left", padx=(0, 10))
    b = ttk.Frame(f)
    b.pack(fill="x", pady=6)
    barra = ttk.Progressbar(f, mode="determinate")
    texto = tk.Text(f, height=16, wrap="word", state="disabled", font=("Consolas", 9))

    def log(m):
        eventos.put(("log", m))

    # 2026-11-06 (captura: "aprieto en analizar pero nada"): un error dentro de un botón
    # no se veía en la ventana. Ahora va al registro de la ventana, a un cartel y a
    # errores_fabrica.txt (junto al programa), con el detalle para mandárselo a Claude.
    import traceback

    def informar_error(ex):
        detalle = traceback.format_exc()
        try:
            with open(Path(__file__).resolve().parent / "errores_fabrica.txt", "a", encoding="utf-8") as fe:
                fe.write(datetime.datetime.now().isoformat(timespec="seconds") + "\n" + detalle + "\n")
        except OSError:
            pass
        log(f"ERROR: {type(ex).__name__}: {ex}")
        log(detalle.strip().splitlines()[-3] if len(detalle.strip().splitlines()) > 2 else detalle)
        log("(el detalle quedó en errores_fabrica.txt, junto al programa: mandáselo a Claude)")
        messagebox.showerror("Error", f"{type(ex).__name__}: {ex}\n\nDetalle en errores_fabrica.txt")

    root.report_callback_exception = lambda tipo, ex, tb: informar_error(ex)

    def numero(k, tipo=int, minimo=0):
        try:
            x = tipo(v[k].get().strip().replace(",", ".") or 0)
        except ValueError:
            raise ValueError(f"'{v[k].get()}' no es un número")
        if x < minimo:
            raise ValueError("Los números no pueden ser negativos")
        return x

    def seleccion():
        p = Path(v["txt"].get().strip())
        if not p.is_file():
            raise ValueError("Elegí un TXT que exista.")
        todos = leer_pedidos(p.read_text(encoding="utf-8-sig"), p.parent)
        a, c = max(1, numero("first")), numero("count")
        sel = todos[a - 1: None if c == 0 else a - 1 + c]
        if not sel:
            raise ValueError("No hay pedidos en ese rango.")
        if not v["dest"].get().strip():
            raise ValueError("Elegí la carpeta de salida.")
        return todos, sel, Path(v["dest"].get().strip())

    def analizar():
        log("Analizando… (lee el TXT y la carpeta de salida)")
        try:
            todos, sel, out = seleccion()
        except Exception as ex:   # noqa: BLE001
            log(f"No se pudo leer: {ex}")
            messagebox.showerror("No se pudo leer", str(ex))
            return

        try:
            precio = numero("precio", float)
        except ValueError:
            precio = 0.0
        repetir = reintentar.get()

        def trabajo():
            try:
                _analizar(todos, sel, out, precio, repetir)
            except Exception as ex:   # noqa: BLE001
                eventos.put(("error", ex))

        threading.Thread(target=trabajo, daemon=True).start()

    def _analizar(todos, sel, out, precio, repetir):
        hechos_viejos = [x for x in out.glob("*.png")] if out.is_dir() else []
        if hechos_viejos and not (out / "final").is_dir():
            log(f"AVISO: hay {len(hechos_viejos)} PNG sueltos en la carpeta de salida (de una versión anterior "
                "de la fábrica). La v3 guarda en final/: movelos a final/ para que no se vuelvan a pagar.")
        estado = leer_estado(out)
        motivos = [ya_hecho(p, out, estado) for p in sel]
        faltan = sum(1 for m in motivos if m is None)
        cambiados = sum(1 for m in motivos if m and "cambió" in m)
        sin_ref = [p["filename"] for p in sel if p["referencia_pedida"] and p["referencia"] is None]
        log(f"{len(todos)} pedidos en el TXT; elegidos {len(sel)}; por hacer {faltan}.")
        if cambiados:
            log(f"AVISO: {cambiados} ya hechos con un pedido distinto al actual (no se rehacen solos).")
        if sin_ref:
            log(f"AVISO: {len(sin_ref)} piden referencia y no la encuentro junto al TXT (ej. {sin_ref[0]}). "
                "Extraé pedidos.zip entero, sin mover el TXT.")
        if precio:
            log(f"Estimado: {faltan} x USD {precio:.3f} = USD {faltan * precio:.2f}"
                + (" (más si repetís las que fallen)" if repetir else ""))
        log("Analizar no gasta nada.")

    def generar():
        try:
            todos, sel, out = seleccion()
            k = clave.get().strip()
            if not k.startswith("sk-"):
                raise ValueError("Falta la API key (empieza con sk-).")
            tope, precio, usd = numero("tope"), numero("precio", float), numero("usd", float)
            if not tope and not usd:
                raise ValueError("Poné un freno de gasto: el máximo de imágenes a pagar (ej. 20) o el máximo en USD (con el precio de cada imagen).")
            if usd and not precio:
                raise ValueError("Para frenar por plata hace falta el precio de cada imagen.")
        except Exception as ex:   # noqa: BLE001
            messagebox.showerror("Revisá", str(ex))
            return
        estado = leer_estado(out)
        n = sum(1 for p in sel if ya_hecho(p, out, estado) is None)
        maximo = min(x for x in (n * (2 if reintentar.get() else 1), tope or 10**9,
                                 int(usd / precio) if usd and precio else 10**9))
        if not messagebox.askyesno("Confirmar", f"Faltan {n}. Como máximo se pagan {maximo} imágenes"
                                   + (f" (USD {maximo * precio:.2f} estimado)" if precio else "")
                                   + f".\nModelo {modelo.get()}, calidad {calidad.get()}.\n¿Empezar?"):
            return
        from openai import OpenAI
        gen = Generador(OpenAI(api_key=k, timeout=180.0, max_retries=0), modelo.get(), calidad.get(),
                        complejidad.get(), log, sin_ref.get())
        parar.clear()
        barra.configure(maximum=len(sel), value=0)
        boton_gen.configure(state="disabled")

        # los valores de la ventana se leen acá: Tk no deja leerlos desde otro hilo
        repetir, mod, cal, con_zip = reintentar.get(), modelo.get(), calidad.get(), hacer_zip.get()

        def trabajo():
            try:
                tanda(sel, out, gen, log, parar, lambda i: eventos.put(("prog", i)), tope, precio, usd,
                      repetir, mod, cal)
                if con_zip:
                    for z in zips(out, todos):
                        log(f"ZIP (solo final/): {z.name}")
            except Exception as ex:   # noqa: BLE001
                log(f"ERROR GENERAL: {type(ex).__name__}: {ex}")
            finally:
                eventos.put(("fin", None))

        threading.Thread(target=trabajo, daemon=True).start()

    def rearmar():
        try:
            todos, _, out = seleccion()
            for z in zips(out, todos):
                log(f"ZIP (solo final/): {z.name}")
            log("ZIP rearmados desde final/ (lo que aprobaste moviéndolo desde revisar/ incluido).")
        except Exception as ex:   # noqa: BLE001
            messagebox.showerror("No se pudo", str(ex))

    ttk.Button(b, text="Analizar TXT (gratis)", command=analizar).pack(side="left")
    boton_gen = ttk.Button(b, text="GENERAR (cuesta)", command=generar)
    boton_gen.pack(side="left", padx=8)
    ttk.Button(b, text="Parar después de la actual", command=parar.set).pack(side="left")
    ttk.Button(b, text="Rearmar ZIP (gratis)", command=rearmar).pack(side="left", padx=8)
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
                elif k == "error":
                    try:
                        raise c
                    except Exception as ex:   # noqa: BLE001
                        informar_error(ex)
        except queue.Empty:
            pass
        root.after(150, mirar)

    log("Primero: Analizar TXT. Probá con Cantidad 1 y mirá hoja_de_contacto.jpg.")
    mirar()
    root.mainloop()


def _faltan_librerias() -> list[str]:
    faltan = []
    for mod in ("PIL", "openai"):
        try:
            __import__(mod)
        except ImportError:
            faltan.append({"PIL": "Pillow"}.get(mod, mod))
    return faltan


if __name__ == "__main__":
    # 2026-11-06 (captura: "No module named 'PIL'" al abrir el .py con doble clic): las
    # librerías están en el .venv que arma INICIAR.bat. Si se abrió con otro Python, se
    # vuelve a abrir solo con el del .venv; si no existe, se explica qué hacer.
    faltan = _faltan_librerias()
    if faltan:
        aqui = Path(__file__).resolve().parent
        venv = aqui / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if venv.exists() and Path(sys.executable).resolve() != venv.resolve():
            import subprocess
            subprocess.Popen([str(venv), str(Path(__file__).resolve())], cwd=str(aqui))
            sys.exit(0)
        mensaje = (f"Faltan librerías ({', '.join(faltan)}).\n\nAbrí la fábrica con INICIAR.bat "
                   "(doble clic): la primera vez las instala. No abras fabrica_hoi4.py directamente.")
        try:
            import tkinter
            from tkinter import messagebox
            tkinter.Tk().withdraw()
            messagebox.showerror("Fábrica HOI4", mensaje)
        except Exception:   # noqa: BLE001
            print(mensaje)
            input("Enter para cerrar")
        sys.exit(1)
    main()
