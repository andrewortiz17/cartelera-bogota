"""Actualiza la cartelera de BogoCine.

Uso (desde la carpeta scrapers/):
    python run.py                 # todas las fuentes
    python run.py cinemark        # solo una o varias fuentes
    python run.py --visible       # abre el navegador a la vista (útil si un sitio bloquea el modo oculto)

Escribe app/www/data/funciones.json, que la app lee al abrir.
"""
import json
import sys
import traceback
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

from comun import BOGOTA_TZ, clave_pelicula, limpiar_titulo, titulo_bonito
from fuentes import cine_colombia, cinemark, cinemateca, cinepolis, procinal, royal_films, viziona

FUENTES = {m.NOMBRE: m for m in (cine_colombia, cinemark, procinal, royal_films, cinepolis, viziona, cinemateca)}
# Cine Colombia bloquea el acceso automatizado a su web (responde 403), así que no se
# consulta por defecto. Se reactiva quitándolo de aquí cuando haya un acuerdo de datos.
DESACTIVADAS = {"cine_colombia"}
SALIDA = Path(__file__).resolve().parents[1] / "app" / "www" / "data" / "funciones.json"


def _misma_pelicula(a: str, b: str) -> bool:
    """'wildwood' ~ 'el bosque salvaje wildwood', 'cars' ~ 'cars una aventura sobre ruedas'.
    Une si todas las palabras del título corto están en el largo, comparten los mismos
    números (para no unir 'Shrek' con 'Shrek 2') y hay al menos una palabra de 5+ letras."""
    pa, pb = set(a.split()), set(b.split())
    corto, largo = (pa, pb) if len(pa) <= len(pb) else (pb, pa)
    if not corto or not corto <= largo:
        return False
    if {w for w in pa if w.isdigit()} != {w for w in pb if w.isdigit()}:
        return False
    if any(len(w) >= 5 for w in corto):
        return True
    # título corto al inicio del largo: 'cars' ~ 'cars una aventura sobre ruedas'
    a, b = sorted((a, b), key=len)
    return len(a) >= 4 and b.startswith(a + " ")


def unificar_titulos(funciones):
    """La misma película se escribe distinto en cada cadena: usa un solo título.
    Agrupa por título normalizado, por título original y por títulos que se contienen."""
    claves = sorted({clave_pelicula(f["pelicula"]) for f in funciones}, key=len)
    padre = {c: c for c in claves}

    def raiz(c):
        while padre[c] != c:
            padre[c] = padre[padre[c]]
            c = padre[c]
        return c

    def unir(a, b):
        ra, rb = raiz(a), raiz(b)
        if ra != rb:
            padre[rb] = ra

    # 1) mismo título original
    por_original = defaultdict(set)
    for f in funciones:
        if f.get("titulo_original"):
            por_original[clave_pelicula(f["titulo_original"])].add(clave_pelicula(f["pelicula"]))
    for grupo in por_original.values():
        g = sorted(grupo)
        for c in g[1:]:
            unir(g[0], c)
    # 2) un título contiene al otro
    for n, a in enumerate(claves):
        for b in claves[n + 1:]:
            if _misma_pelicula(a, b):
                unir(a, b)

    grupos = defaultdict(list)
    for f in funciones:
        grupos[raiz(clave_pelicula(f["pelicula"]))].append(f)
    for fs in grupos.values():
        # Prefiere el título más común; si empatan, el más completo; evita los que vienen en MAYÚSCULAS
        conteo = Counter(limpiar_titulo(f["pelicula"]) for f in fs)
        elegido = titulo_bonito(max(conteo, key=lambda t: (not t.isupper(), conteo[t], len(t))))
        original = next((f["titulo_original"] for f in fs if f["titulo_original"]), "")
        for f in fs:
            f["pelicula"] = elegido
            f["titulo_original"] = f["titulo_original"] or original


def unificar_por_tmdb(funciones, info):
    """Con TMDB: la misma película (mismo id) queda con un solo título, el de TMDB en español."""
    for f in funciones:
        dato = info.get(f["pelicula"])
        if dato and dato.get("titulo_tmdb"):
            f["pelicula"] = dato["titulo_tmdb"]


def main():
    # La consola de Windows no siempre usa UTF-8
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    elegidas = {n: FUENTES[n] for n in args} if args else {n: m for n, m in FUENTES.items() if n not in DESACTIVADAS}
    estado, funciones = {}, []

    anterior = {}
    if SALIDA.exists():
        try:
            anterior = json.loads(SALIDA.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    with sync_playwright() as p:
        navegador = p.chromium.launch(headless="--visible" not in sys.argv)
        contexto = navegador.new_context(locale="es-CO", timezone_id="America/Bogota")
        for nombre, modulo in elegidas.items():
            print(f"→ {nombre}")
            try:
                fs = [f.dict() for f in modulo.obtener(contexto)]
                funciones += fs
                estado[nombre] = {"funciones": len(fs), "error": None if fs else "0 funciones: revisar"}
            except Exception as e:  # una fuente rota no detiene las demás
                traceback.print_exc()
                estado[nombre] = {"funciones": 0, "error": f"{type(e).__name__}: {e}"[:300]}
        navegador.close()

    # Si solo se corrieron algunas fuentes, conserva las funciones de las demás
    if args and anterior:
        funciones += [f for f in anterior.get("funciones", []) if f.get("fuente") not in elegidas]
        estado = {**anterior.get("estado", {}), **estado}

    # Quita repetidas (algunas páginas muestran la misma función dos veces)
    vistas, unicas = set(), []
    for f in funciones:
        clave = (f["sala_id"], clave_pelicula(f["pelicula"]), f["hora"], f.get("idioma", ""))
        if clave not in vistas:
            vistas.add(clave)
            unicas.append(f)
    funciones = unicas

    unificar_titulos(funciones)
    funciones.sort(key=lambda f: (f["hora"], f["sala_id"]))
    print("→ posters")
    try:
        import posters
        info = posters.agregar(funciones)
        unificar_por_tmdb(funciones, info)
        mapa_posters = {d["titulo_tmdb"] or t: d["poster"] for t, d in info.items() if d.get("poster")}
    except Exception as e:  # sin pósters la cartelera igual sirve
        print(f"  posters: {type(e).__name__}: {e}")
        mapa_posters = {}
    datos = {"generado": datetime.now(BOGOTA_TZ).isoformat(timespec="seconds"),
             "estado": estado, "posters": mapa_posters, "funciones": funciones}
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\nResumen:")
    for n, e in estado.items():
        print(f"  {'✔' if not e['error'] else '✖'} {n}: {e['funciones']} funciones {e['error'] or ''}")
    print(f"\nGuardado en {SALIDA}")


if __name__ == "__main__":
    main()
