"""Fuente: Cine Colombia (cadena comercial).

TODO:
1. Abrir la web de Cine Colombia en el navegador del computador con DevTools → pestaña Network → filtro Fetch/XHR.
2. Elegir una sala de Bogotá y buscar la petición que trae la cartelera (suele ser JSON).
3. Copiar esa URL y sus parámetros aquí, y mapear cada función a models.Funcion.
4. Guardar el id interno de cada sala de Cine Colombia en salas.json (campo extra, p. ej. "id_fuente").
Revisar los términos de uso del sitio y no hacer más de unas pocas peticiones al día.
"""
from app.sources.base import FuentePendiente


class CineColombia(FuentePendiente):
    nombre = "cine_colombia"
