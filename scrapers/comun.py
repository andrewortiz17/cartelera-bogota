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
# Cuántos días se leen en las cadenas que publican por pestañas (hoy + los siguientes).
# Se puede cambiar sin tocar el código con la variable de entorno BOGOCINE_DIAS.
import os as _os
DIAS_A_LEER = max(1, int(_os.environ.get("BOGOCINE_DIAS", "3")))
USER_AGENT = "BogoCine/0.4 (cartelera de Bogota; https://github.com/andrewortiz17/cartelera-bogota)"


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
    poster: str = ""               # imagen que publica el propio cine

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
    # Cinemark marca su "Temporada Siniestra" con TS: 'BACKROOMS TS', 'POLTERGEIST TS4'
    t = re.sub(r"\s+TS\d*$", "", t, flags=re.I)
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


# Lee las imágenes de la página con el texto que las rodea (alt y las primeras líneas
# del bloque que las contiene). Así se puede saber de qué película es cada póster.
_JS_IMAGENES = """() => [...document.querySelectorAll('img')].map(i => {
  const src = i.currentSrc || i.src || i.dataset.src || '';
  if (!src || src.startsWith('data:') || /\\.svg(\\?|$)|logo|icon|banner/i.test(src)) return null;
  let c = i, textos = [i.alt || ''];
  for (let k = 0; k < 6 && c; k++) {
    c = c.parentElement;
    const t = (c && c.innerText || '').trim();
    if (t) { textos = textos.concat(t.split('\\n').slice(0, 4)); break; }
  }
  return { src, textos };
}).filter(Boolean)"""


def imagenes_en_pagina(pagina) -> list[dict]:
    try:
        return pagina.evaluate(_JS_IMAGENES)
    except Exception:
        return []


def asignar_posters(funciones: list, imagenes: list[dict]) -> None:
    """Pone en cada función el póster cuya descripción coincide con su título."""
    indice = {}
    for img in imagenes:
        for t in img["textos"]:
            c = clave_pelicula(limpiar_titulo(t or ""))
            if len(c) >= 2 and c not in indice:
                indice[c] = img["src"]
    for f in funciones:
        if f.poster:
            continue
        for t in (f.pelicula, f.titulo_original):
            c = clave_pelicula(limpiar_titulo(t or ""))
            if c in indice:
                f.poster = indice[c]
                break


def dias_a_leer() -> list[date]:
    """Hoy y los días siguientes que se intentan leer en cada cadena."""
    return [hoy() + timedelta(days=k) for k in range(DIAS_A_LEER)]


def patron_fecha(dia: date) -> str:
    """Expresión que reconoce la pestaña de un día en las webs de los cines:
    'JUE. 05 NOV. 2026' (Cinemark), 'Jue, Nov 5 2026' (Procinal, Viziona),
    'Mañana (05 noviembre)' (Cinépolis), 'JUE 05 nov' (Royal Films)."""
    mes = [k for k, v in MESES_CORTOS.items() if v == dia.month][0]
    d = rf"(?<!\d)0?{dia.day}(?!\d)"
    return rf"({d}\W*(de\s+)?{mes}|{mes}[a-z]*\.?\W*{d})"


# Busca el elemento más pequeño cuyo texto (corto) coincide con la fecha, prefiriendo los
# que se pueden tocar (botones, enlaces, pestañas). Devuelve su posición en la página, si
# está marcado como elegido (clase "selected"/"active" o aria-selected) y, si `marcar`,
# lo deja marcado para que Playwright haga clic en él como lo haría una persona.
_JS_BUSCAR_DIA = """([patron, marcar]) => {
  document.querySelectorAll('[data-bogocine-dia]').forEach(e => e.removeAttribute('data-bogocine-dia'));
  const re = new RegExp(patron, 'i');
  const TOCABLE = 'button,a,[role=tab],[role=button],[role=option],li,label,option';
  const todos = [...document.querySelectorAll('body *')];
  const coinciden = todos.filter(el => {
    const t = (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
    return t && t.length <= 40 && re.test(t);
  });
  let hojas = coinciden.filter(el => !coinciden.some(o => o !== el && el.contains(o)));
  const tocables = hojas.filter(el => el.closest(TOCABLE) || getComputedStyle(el).cursor === 'pointer');
  if (tocables.length) hojas = tocables;
  if (!hojas.length) return null;
  const el = hojas[0];
  const destino = el.tagName === 'OPTION' ? el : (el.closest(TOCABLE) || el);
  const elegido = (() => {
    if (el.tagName === 'OPTION') return el.selected;
    const marca = /(^|[\\s_-])(selected|active|current|is-active|activ[oa]|seleccionad[oa])([\\s_-]|$)/i;
    for (let n = destino, k = 0; n && k < 4; n = n.parentElement, k++) {
      if (n.getAttribute('aria-selected') === 'true' || n.getAttribute('aria-current') ||
          marca.test(typeof n.className === 'string' ? n.className : '')) return true;
    }
    return false;
  })();
  const res = {indice: todos.indexOf(el), elegido};
  if (!marcar) return res;
  if (el.tagName === 'OPTION') {
    const sel = el.closest('select'); sel.value = el.value;
    sel.dispatchEvent(new Event('input', {bubbles: true}));
    sel.dispatchEvent(new Event('change', {bubbles: true}));
    res.select = true;
    return res;
  }
  destino.setAttribute('data-bogocine-dia', '1');
  return res;
}"""


def buscar_dia(pagina, dia: date):
    """{'indice', 'elegido'} de la pestaña del día, o None si no hay pestaña."""
    try:
        return pagina.evaluate(_JS_BUSCAR_DIA, [patron_fecha(dia), False])
    except Exception:
        return None


def elegir_dia(pagina, dia: date, espera_ms: int = 2500):
    """Hace clic en la pestaña u opción del día `dia`. Devuelve (texto_de_la_página, cambió,
    quedó_elegida) o None si no hay pestaña para ese día."""
    try:
        antes = pagina.inner_text("body")
        r = pagina.evaluate(_JS_BUSCAR_DIA, [patron_fecha(dia), True])
        if not r:
            return None
        if not r.get("select"):
            try:
                pagina.click("[data-bogocine-dia]", timeout=4000)
            except Exception:
                pagina.eval_on_selector("[data-bogocine-dia]", "e => e.click()")
        pagina.wait_for_timeout(espera_ms)
        despues = pagina.inner_text("body")
        # Algunas webs (Cinemark) cargan los horarios del día con retraso: se espera hasta
        # ~6 s más mientras la página siga igual.
        for _ in range(9):
            if despues != antes:
                break
            pagina.wait_for_timeout(700)
            despues = pagina.inner_text("body")
        tras = buscar_dia(pagina, dia) or {}
        return despues, despues != antes, bool(tras.get("elegido"))
    except Exception as e:
        print(f"    no se pudo elegir el día {dia}: {type(e).__name__}: {str(e).splitlines()[0][:100]}")
        return None


def leer_varios_dias(pagina, texto_inicial: str, parsear_dia, etiqueta: str,
                     repite_programacion: bool = False) -> list:
    """Lee cada día que tenga pestaña. Ojo: de noche algunas webs (Procinal) ya abren en el
    día siguiente y quitan la pestaña de hoy, y otras repiten la misma programación varios
    días. Un día se acepta si al elegirlo la página cambia o, en webs que repiten la misma
    programación (`repite_programacion`, p. ej. Procinal), si su pestaña queda marcada como
    elegida aunque el texto sea igual. En las demás eso suele ser que no alcanzó a cargar. El texto inicial se asigna al
    día cuya pestaña venga marcada como elegida o, si no se sabe, a la primera pestaña.
    Nunca se copian los horarios de un día a otro sin una de esas señales.
    `parsear_dia(texto, dia)` devuelve las funciones de ese día."""
    if not texto_inicial:
        return []
    dias = dias_a_leer()
    info = {d: buscar_dia(pagina, d) for d in dias}
    con_pestana = [d for d in dias if info[d]]
    if not con_pestana:                      # página de un solo día, sin pestañas
        return parsear_dia(texto_inicial, dias[0])
    marcados = [d for d in con_pestana if info[d].get("elegido")]
    inicial = marcados[0] if len(marcados) == 1 else min(con_pestana, key=lambda d: info[d]["indice"])
    out, actual = [], texto_inicial
    for dia in con_pestana:
        r = elegir_dia(pagina, dia)
        if r is None:
            continue
        texto, cambio, elegida = r
        if not (cambio or (elegida and repite_programacion) or (dia == inicial and actual == texto_inicial)):
            print(f"    {etiqueta} {dia:%d/%m}: la página no cambió al elegirlo, se omite")
            continue
        actual = texto
        nuevas = parsear_dia(texto, dia)
        print(f"    {etiqueta} {dia:%d/%m}: {len(nuevas)} funciones")
        out += nuevas
    return out
