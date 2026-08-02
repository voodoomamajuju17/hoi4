"""Errores del generador.

Filosofía: el generador falla RUIDOSAMENTE en tiempo de generación antes que
producir un archivo que HOI4 no carga. Un error acá cuesta segundos; el mismo
error en error.log cuesta una sesión de debug.
"""


class GenError(Exception):
    """Error fatal de generación."""

    def __init__(self, message: str, *, hint: str | None = None, where: str | None = None):
        self.message = message
        self.hint = hint
        self.where = where
        super().__init__(message)

    def __str__(self) -> str:
        parts = []
        if self.where:
            parts.append(f"[{self.where}]")
        parts.append(self.message)
        text = " ".join(parts)
        if self.hint:
            text += f"\n  -> {self.hint}"
        return text


class SpecError(GenError):
    """El spec es inválido o incoherente."""


class VanillaError(GenError):
    """Falta la instalación vanilla, o no se pudo leer lo que hacía falta."""


class LocalisationError(GenError):
    """Violación de la regla de cero claves huérfanas."""


class BlockedError(GenError):
    """Falta un dato del spec que todavía no fue respondido (una Qxxx abierta)."""

    def __init__(self, message: str, question: str, *, hint: str | None = None):
        self.question = question
        super().__init__(
            f"{message} (bloqueado por {question})",
            hint=hint or f"Ver spec/99_open_questions.yaml -> {question}",
        )
