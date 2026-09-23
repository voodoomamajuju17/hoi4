# Empezar — guía paso a paso

No hace falta que sepas Python, git ni nada de esto. Son 4 pasos.

---

## Paso 1 — Tener Python

Abrí una terminal y escribí:

```
py --version
```

(en Mac o Linux: `python3 --version`)

- **Si te contesta algo como `Python 3.12.1`** → listo, seguí al paso 2.
- **Si dice que no lo encuentra** → instalalo de https://www.python.org/downloads/
  **En Windows, durante la instalación marcá la casilla "Add Python to PATH".**
  Es fácil pasarla por alto y sin eso el paso 2 no funciona.

> ¿Cómo abro una terminal?
> **Windows:** tecla Windows, escribí `cmd`, Enter.
> **Mac:** Cmd+Espacio, escribí `Terminal`, Enter.

---

## Paso 2 — Bajar este repo

Andá a la página del repo en GitHub → botón verde **Code** → **Download ZIP**.

Descomprimilo donde quieras, por ejemplo en el Escritorio. Vas a tener una
carpeta con `empezar.py` adentro.

---

## Paso 3 — Correr el script

En la terminal, entrá a esa carpeta y corré el script:

```
cd Desktop\hoi4-main
py empezar.py
```

En Mac o Linux:

```
cd ~/Desktop/hoi4-main
python3 empezar.py
```

En Windows también podés simplemente **hacer doble click en `empezar.bat`**.

El script hace todo solo: busca tu Hearts of Iron IV, instala lo que falte,
genera el mod y lo copia a tu carpeta de mods.

### Si te dice "No encontre el juego solo"

Pasale la ruta a mano:

1. Abrí Steam
2. Click derecho sobre **Hearts of Iron IV** → **Administrar** → **Explorar archivos locales**
3. Se abre el explorador. Copiá la ruta de la barra de arriba.
4. Corré de nuevo, pegando esa ruta entre comillas:

```
py empezar.py "C:\Program Files (x86)\Steam\steamapps\common\Hearts of Iron IV"
```

**Dos confusiones típicas:**

| Esto NO | Esto SÍ |
|---|---|
| `...\Hearts of Iron IV\hoi4.exe` (el ejecutable) | `...\Hearts of Iron IV` (la carpeta que lo contiene) |
| `Documentos\Paradox Interactive\...\mod` (carpeta de mods) | `...\steamapps\common\Hearts of Iron IV` (instalación) |

Sabés que agarraste la correcta si adentro ves las carpetas `common`, `history`
y `map`.

---

## Paso 4 — Abrir el juego y pasarme el resultado

1. Abrí el launcher de Hearts of Iron IV
2. Andá a **Mods** y activá **2100 Meganations**
3. Dale a jugar

> ### Ojo: todavía NO es jugable
>
> Esto es una **prueba de humo**, no el mod. Ahora mismo tiene los 10 países,
> las ideologías, las ideas nacionales y el árbol de focos del EFE, a Aurelio IV
> y el BioSteel (el carbón renombrado), pero **todavía no tiene territorio**:
> los países existen pero no aparecen en el mapa. Eso viene después.
>
> Lo único que estamos probando es que el launcher lo liste y que el juego
> llegue al menú sin romperse. Si esperás una partida jugable te vas a
> decepcionar, y no es que esté fallando.

**Pasame estas dos cosas:**

1. El archivo **`reporte.txt`**, que queda en la misma carpeta del script.
2. Si el juego tira algún error, el **`error.log`**, que está en:
   `Documentos\Paradox Interactive\Hearts of Iron IV\logs\error.log`

Con eso corrijo el generador y seguimos con el territorio.

---

## Preguntas razonables

**¿Esto me rompe el juego?**
No. El script solo **lee** tu instalación de HOI4, nunca escribe ahí. Lo único
que crea es una carpeta nueva dentro de tu carpeta de mods. Para desinstalar,
borrás esa carpeta y listo.

**¿Y mis partidas guardadas?**
No se tocan. Un mod nunca afecta partidas de otro mod ni de vanilla.

**¿Por qué necesita mi instalación del juego?**
Porque prefiero que el generador **lea** los archivos de HOI4 antes que adivinar
su contenido. Los IDs de las provincias y la estructura interna de las
ideologías cambian entre versiones: leyéndolos, siempre da bien; escribiéndolos
de memoria, un dato mal puesto rompe la carga o —peor— reasigna territorio en
silencio sin dar ningún error.

**Corrí el script pero no entendí nada de lo que salió.**
No importa. Pasame `reporte.txt` tal cual y yo lo leo.
