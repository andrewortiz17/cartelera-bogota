"""Fuente: carga manual (cineclubes, salas independientes).

Lee funciones de manual.json, que se llena con el endpoint POST /admin/funciones
(o a mano). Más adelante: extracción desde pósters de Instagram con OCR/visión.
"""
import json
from pathlib import Path

from app.models import Funcion, Sala
from app.sources.base import Fuente

ARCHIVO = Path(__file__).resolve().parents[2] / "manual.json"


def leer() -> list[dict]:
    if ARCHIVO.exists():
        return json.loads(ARCHIVO.read_text(encoding="utf-8"))
    return []


def guardar(filas: list[dict]) -> None:
    ARCHIVO.write_text(json.dumps(filas, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


class Manual(Fuente):
    nombre = "manual"

    async def obtener(self, salas: list[Sala]) -> list[Funcion]:
        ids = {s.id for s in salas}
        return [Funcion(**f) for f in leer() if f["sala_id"] in ids]
