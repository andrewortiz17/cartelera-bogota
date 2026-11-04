"""Utilidades compartidas por todos los scrapers de BogoCine."""
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone

BOGOTA_TZ = timezone(timedelta(hours=-5))
MESES = {m: i for i, m in enumerate(
    ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
     "agosto", "septiembre", "octubre", "noviembre", "diciembre"], start=1)}
MESES_CORTOS = {k[:3]: v for k, v in MESES.items()}

# Pausa entre páginas para no cargar los sitios
PAUSA_SEGUNDOS = 2.5
USER_AGENT = "BogoCine/0.3 (proyecto personal; cartelera de Bogotá)"


@dataclass
class Funcion:
    sala_id: str
    pelicula: str
    hora: str                      # ISO 8601 con zona -05:00
    titulo_original: str = ""
    formato: str = ""
    idioma: str = ""
    clasificacion: str = ""
    duracion_min: int | None = None
    url_compra: str = ""
    fuente: str = ""

    def dict(self):
        return asdict(self)


def limpiar_lineas(texto: str) -> list[str]:
    return [l.strip() for l in texto.replace("ㅤ", "").splitlines() if l.strip()]


def hora_a_24(texto: str) -> tuple[int, int] | None:
    """Convierte '12:40P.M.', '09:10 p. m.', '6:30 pm' o '14:35' a (h, m)."""
    t = re.sub(r"[\s.]", "", texto.lower())   # incluye espacios no separables (\xa0)
    m = re.fullmatch(r"(\d{1,2}):(\d{2})(am|pm)?", t)
    if not m:
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2)), m.group(3)
    if ap == "pm" and h != 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    if h > 23 or mi > 59:
        return None
    return h, mi


def iso(dia: date, hm: tuple[int, int]) -> str:
    h, m = hm
    # Funciones de madrugada (00:00–03:59) pertenecen al día siguiente
    extra = 1 if h < 4 else 0
    d = datetime(dia.year, dia.month, dia.day, h, m, tzinfo=BOGOTA_TZ) + timedelta(days=extra)
    return d.isoformat()


def hoy() -> date:
    return datetime.now(BOGOTA_TZ).date()


def sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def clave_pelicula(titulo: str) -> str:
    """Clave para reconocer la misma película entre cadenas."""
    t = sin_tildes(titulo.lower())
    t = re.sub(r"\((re ?estreno|reestreno)\)|^re:\s*|^reestreno\s*-?\s*|\bre\b$", "", t)
    t = re.sub(r"\b(25 aniversario)\b", "", t)
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def titulo_bonito(titulo: str) -> str:
    """'LOS JUEGOS DEL HAMBRE' -> 'Los juegos del hambre' (solo si viene en mayúsculas)."""
    if titulo.isupper():
        titulo = titulo.lower()
    return titulo[:1].upper() + titulo[1:]


def limpiar_titulo(titulo: str) -> str:
    """Quita marcas de reestreno ('RE: Cars', 'SHREK RE', 'Shrek (Reestreno)')."""
    t = re.sub(r"^(RE:|REESTRENO\s*-?)\s*", "", titulo, flags=re.I)
    t = re.sub(r"\s*\((re ?estreno)\)\s*$|\s+re$", "", t, flags=re.I)
    return t.strip()


def abrir(pagina, url: str, esperar: str | None = None, extra_ms: int = 1500):
    """Abre una página sin esperar 'networkidle' (los sitios con analítica nunca quedan
    quietos). Espera a que aparezca el texto `esperar` (si se da) y luego `extra_ms`.
    Devuelve el texto visible de la página, o "" si no cargó."""
    try:
        resp = pagina.goto(url, wait_until="domcontentloaded", timeout=45000)
        if resp is not None and resp.status >= 400:
            print(f"    {url} respondió {resp.status}")
            return ""
        if esperar:
            try:
                pagina.get_by_text(re.compile(esperar, re.I)).first.wait_for(timeout=25000)
            except Exception:
                print(f"    {url}: no apareció «{esperar}» (puede no haber funciones hoy)")
        pagina.wait_for_timeout(extra_ms)
        return pagina.inner_text("body")
    except Exception as e:
        print(f"    {url}: {type(e).__name__}: {str(e).splitlines()[0][:120]}")
        return ""
