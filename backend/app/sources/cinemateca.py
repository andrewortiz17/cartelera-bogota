"""Fuente: Cinemateca de Bogotá (sede principal, El Tunal, Fontanar del Río).

TODO: la programación se publica en cinematecadebogota.gov.co y en notas de
bogota.gov.co. Probablemente toque parsear HTML con BeautifulSoup. Las
funciones de cineclubes de la franja "Vive la Cinemateca" llegan por aquí.
"""
from app.sources.base import FuentePendiente


class Cinemateca(FuentePendiente):
    nombre = "cinemateca"
