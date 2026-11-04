"""API de BogoCine (borrador).

Arranque local:  uvicorn app.main:app --reload   (desde la carpeta backend/)
"""
import asyncio
import json
import math
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.models import EstadoFuente, Funcion, Sala
from app.sources import FUENTES
from app.sources import manual

TZ = ZoneInfo("America/Bogota")
SALAS_PATH = Path(os.getenv("SALAS_PATH", Path(__file__).resolve().parents[2] / "app/www/data/salas.json"))
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "cambia-esto")
INTERVALO_HORAS = 6

app = FastAPI(title="BogoCine")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SALAS: list[Sala] = [Sala(**s) for s in json.loads(SALAS_PATH.read_text(encoding="utf-8"))["salas"]]
FUNCIONES: list[Funcion] = []
ESTADO: dict[str, EstadoFuente] = {n: EstadoFuente(fuente=n) for n in FUENTES}


def distancia_km(lat1, lng1, lat2, lng2) -> float:
    """Haversine. Para producción: PostGIS (ST_DistanceSphere)."""
    r = math.radians
    h = math.sin(r(lat2 - lat1) / 2) ** 2 + math.cos(r(lat1)) * math.cos(r(lat2)) * math.sin(r(lng2 - lng1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


async def actualizar() -> None:
    """Corre todas las fuentes. Una fuente rota no tumba a las demás."""
    global FUNCIONES
    nuevas: list[Funcion] = []
    for nombre, fuente in FUENTES.items():
        est = ESTADO[nombre]
        est.ultima_corrida = datetime.now(TZ)
        salas = [s for s in SALAS if s.fuente == nombre]
        try:
            fs = await fuente.obtener(salas)
            nuevas.extend(fs)
            est.funciones, est.error, est.ultima_exitosa = len(fs), None, datetime.now(TZ)
            if not fs and salas:
                est.error = "0 funciones: posible scraper roto"
        except NotImplementedError as e:
            est.error = str(e)
        except Exception as e:  # noqa: BLE001
            est.error = f"{type(e).__name__}: {e}"
    FUNCIONES = nuevas


async def bucle_actualizacion() -> None:
    while True:
        await actualizar()
        await asyncio.sleep(INTERVALO_HORAS * 3600)


@app.on_event("startup")
async def inicio() -> None:
    asyncio.create_task(bucle_actualizacion())


@app.get("/salas", response_model=list[Sala])
def listar_salas(tipo: str | None = None):
    return [s for s in SALAS if tipo is None or s.tipo == tipo]


@app.get("/funciones", response_model=list[Funcion])
def listar_funciones(sala_id: str | None = None, pelicula: str | None = None):
    desde = datetime.now(TZ) - timedelta(minutes=10)
    return sorted(
        (f for f in FUNCIONES
         if f.hora >= desde
         and (sala_id is None or f.sala_id == sala_id)
         and (pelicula is None or pelicula.lower() in f.pelicula.lower())),
        key=lambda f: f.hora,
    )


@app.get("/cercanas")
def cercanas(
    lat: float, lng: float,
    radio_km: float = Query(5, gt=0, le=50),
    proxima_hora: bool = False,
):
    """Salas ordenadas por distancia en línea recta.
    Siguiente paso: tiempo de viaje con OpenRouteService/OSRM para las 5–10 más cercanas."""
    ahora = datetime.now(TZ)
    out = []
    for s in SALAS:
        if s.lat is None or s.lng is None:
            continue
        d = distancia_km(lat, lng, s.lat, s.lng)
        if d > radio_km:
            continue
        fs = [f for f in FUNCIONES if f.sala_id == s.id and f.hora >= ahora]
        if proxima_hora:
            fs = [f for f in fs if f.hora <= ahora + timedelta(hours=1)]
            if not fs:
                continue
        out.append({"sala": s, "distancia_km": round(d, 2), "funciones": sorted(fs, key=lambda f: f.hora)})
    return sorted(out, key=lambda x: x["distancia_km"])


@app.get("/fuentes/estado", response_model=list[EstadoFuente])
def estado_fuentes():
    return list(ESTADO.values())


def _auth(token: str | None) -> None:
    if token != ADMIN_TOKEN:
        raise HTTPException(401, "Token inválido")


@app.post("/admin/actualizar")
async def forzar_actualizacion(x_token: str | None = Header(None)):
    _auth(x_token)
    await actualizar()
    return {"funciones": len(FUNCIONES)}


@app.post("/admin/funciones")
async def cargar_funciones_manuales(funciones: list[Funcion], x_token: str | None = Header(None)):
    """Formulario para cineclubes y salas independientes."""
    _auth(x_token)
    ids = {s.id for s in SALAS}
    malas = [f.sala_id for f in funciones if f.sala_id not in ids]
    if malas:
        raise HTTPException(400, f"Salas desconocidas: {sorted(set(malas))}")
    manual.guardar(manual.leer() + [f.model_dump(mode="json") for f in funciones])
    await actualizar()
    return {"agregadas": len(funciones)}
