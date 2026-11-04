"""Interfaz común: cada fuente devuelve funciones normalizadas.

Agregar una fuente nueva = crear un archivo en este paquete con una clase que
herede de Fuente y registrarla en sources/__init__.py. Si una fuente falla,
las demás siguen funcionando.
"""
from abc import ABC, abstractmethod
from app.models import Funcion, Sala


class Fuente(ABC):
    nombre: str = "base"

    @abstractmethod
    async def obtener(self, salas: list[Sala]) -> list[Funcion]:
        """Recibe las salas que pertenecen a esta fuente y devuelve sus funciones."""


class FuentePendiente(Fuente):
    """Marcador para fuentes cuyo scraper aún no está escrito."""

    async def obtener(self, salas: list[Sala]) -> list[Funcion]:
        raise NotImplementedError(
            f"Scraper '{self.nombre}' pendiente. Ver TODO en el archivo de la fuente."
        )
