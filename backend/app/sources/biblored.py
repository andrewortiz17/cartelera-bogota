"""Fuente: cineclubes de BibloRed (bibliotecas públicas).

TODO: las sesiones aparecen como notas en bogota.gov.co ("que-hacer/cultura").
Buscar notas con 'cineclub' y extraer fecha, hora y película del texto.
"""
from app.sources.base import FuentePendiente


class Biblored(FuentePendiente):
    nombre = "biblored"
