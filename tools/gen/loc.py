"""Localisation con garantía de cero claves huérfanas.

Regla dura del proyecto: la localisation viaja siempre con el contenido que la
usa. Acá eso se hace verificable en vez de aspiracional.

Los emisores tienen que llamar:

    loc.define("EFE_mandato_verde", en="The Green Mandate", es="El Mandato Verde")
    loc.reference("EFE_mandato_verde")   # cada vez que la clave se escribe en un .txt

Al cerrar, `verify()` compara los dos conjuntos y falla si no coinciden:

  - definida pero nunca referenciada -> clave muerta, texto que nadie ve
  - referenciada pero nunca definida -> el jugador ve la clave cruda en pantalla

Las dos son bugs. La segunda es visible y vergonzosa; la primera es basura que
se acumula hasta que nadie sabe qué se puede borrar.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .errors import LocalisationError

LANGUAGES = {"english": "en", "spanish": "es"}


class LocRegistry:
    def __init__(self) -> None:
        # clave -> idioma -> texto
        self._defined: dict[str, dict[str, str]] = {}
        # clave -> archivo lógico donde vive
        self._file_of: dict[str, str] = {}
        self._referenced: set[str] = set()
        # de dónde vino cada referencia, para que el mensaje de error sirva
        self._ref_origin: dict[str, list[str]] = defaultdict(list)
        self._def_origin: dict[str, str] = {}

    # -- API de los emisores ------------------------------------------------

    def define(self, key: str, *, en: str, es: str, file: str, origin: str = "") -> str:
        """Define una clave en los dos idiomas. Devuelve la clave, para encadenar."""
        if key in self._defined:
            prev = self._def_origin.get(key, "?")
            raise LocalisationError(
                f"clave de localisation duplicada: '{key}'",
                hint=f"definida primero en {prev}, de nuevo en {origin or '?'}",
            )
        for lang, text in (("english", en), ("spanish", es)):
            if text is None or not str(text).strip():
                raise LocalisationError(
                    f"clave '{key}' sin texto en {lang}",
                    hint="toda clave necesita EN y ES. Ver 00_project.yaml -> constraints.localisation",
                )
        self._defined[key] = {"english": _clean(en), "spanish": _clean(es)}
        self._file_of[key] = file
        self._def_origin[key] = origin
        return key

    def reference(self, key: str, origin: str = "") -> str:
        """Marca que un archivo del mod escribe esta clave. Devuelve la clave."""
        self._referenced.add(key)
        if origin:
            self._ref_origin[key].append(origin)
        return key

    def define_and_reference(self, key: str, *, en: str, es: str, file: str, origin: str = "") -> str:
        self.define(key, en=en, es=es, file=file, origin=origin)
        return self.reference(key, origin)

    # -- Verificación -------------------------------------------------------

    def verify(self) -> None:
        defined = set(self._defined)
        undefined = self._referenced - defined
        unused = defined - self._referenced

        problems: list[str] = []
        if undefined:
            lines = []
            for key in sorted(undefined)[:20]:
                origins = ", ".join(dict.fromkeys(self._ref_origin.get(key, [])))
                lines.append(f"    {key}" + (f"  (usada en {origins})" if origins else ""))
            more = f"\n    ... y {len(undefined) - 20} mas" if len(undefined) > 20 else ""
            problems.append(
                f"  {len(undefined)} clave(s) REFERENCIADAS SIN DEFINIR "
                f"(el jugador veria la clave cruda en pantalla):\n" + "\n".join(lines) + more
            )
        if unused:
            lines = [f"    {k}  (definida en {self._def_origin.get(k, '?')})" for k in sorted(unused)[:20]]
            more = f"\n    ... y {len(unused) - 20} mas" if len(unused) > 20 else ""
            problems.append(
                f"  {len(unused)} clave(s) DEFINIDAS SIN USAR (texto muerto):\n" + "\n".join(lines) + more
            )

        if problems:
            raise LocalisationError(
                "la localisation no cierra:\n" + "\n".join(problems),
                hint="regla del proyecto: cero claves huerfanas. Ni de mas ni de menos.",
            )

    # -- Escritura ----------------------------------------------------------

    def write(self, mod_root: Path) -> list[Path]:
        """Escribe localisation/<idioma>/<archivo>_l_<idioma>.yml.

        HOI4 exige UTF-8 CON BOM. Sin BOM el juego ignora el archivo en
        silencio y el jugador ve las claves crudas: es el error de
        localisation mas comun y el mas dificil de ver mirando el texto.
        """
        by_file: dict[str, list[str]] = defaultdict(list)
        for key, texts in self._defined.items():
            by_file[self._file_of[key]].append(key)

        written: list[Path] = []
        for language in LANGUAGES:
            out_dir = mod_root / "localisation" / language
            out_dir.mkdir(parents=True, exist_ok=True)
            for logical_file, keys in sorted(by_file.items()):
                # Un archivo logico "replace/x" va a localisation/<idioma>/replace/:
                # lo que esta ahi pisa las claves vanilla con el mismo nombre.
                path = out_dir / f"{logical_file}_l_{language}.yml"
                path.parent.mkdir(parents=True, exist_ok=True)
                lines = [f"l_{language}:"]
                for key in sorted(keys):
                    text = self._defined[key][language]
                    lines.append(f' {key}:0 "{text}"')
                path.write_bytes(("\n".join(lines) + "\n").encode("utf-8-sig"))
                written.append(path)
        return written

    # -- Introspección ------------------------------------------------------

    @property
    def key_count(self) -> int:
        return len(self._defined)

    def stats(self) -> str:
        return (
            f"{len(self._defined)} claves x {len(LANGUAGES)} idiomas "
            f"= {len(self._defined) * len(LANGUAGES)} entradas"
        )


def _clean(text: str) -> str:
    """Normaliza texto para una línea de .yml de Paradox."""
    text = " ".join(str(text).split())
    return text.replace('"', "'")
