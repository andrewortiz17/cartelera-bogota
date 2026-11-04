from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel

TipoSala = Literal["cadena", "cinemateca", "independiente", "cineclub"]


class Sala(BaseModel):
    id: str
    nombre: str
    operador: str
    tipo: TipoSala
    zona: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    fuente: str                      # nombre del módulo en app/sources
    verificado: bool = False
    nota: Optional[str] = None


class Funcion(BaseModel):
    sala_id: str
    pelicula: str                    # título normalizado (idealmente emparejado con TMDB)
    titulo_original_fuente: str = "" # tal como lo publica la cadena
    hora: datetime
    formato: str = ""                # 2D, 3D, IMAX, XD…
    idioma: str = ""                 # Doblada / Subtitulada
    url_compra: Optional[str] = None
    tmdb_id: Optional[int] = None


class EstadoFuente(BaseModel):
    fuente: str
    ultima_corrida: Optional[datetime] = None
    ultima_exitosa: Optional[datetime] = None
    funciones: int = 0
    error: Optional[str] = None
