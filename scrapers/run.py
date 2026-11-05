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
from fuentes import (cine_colombia, cinemania, cinemark, cinemateca, cinepolis, elmuro, manual, procinal,
                     royal_films, viziona)

FUENTES = {m.NOMBRE: m for m in (cine_colombia, cinemark, procinal, royal_films, cinepolis, viziona, cinemateca,
                                       cinemania, elmuro, manual)}
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


def unificar_titulos(funciones, qids=None):
    """La misma película se escribe distinto en cada cadena: usa un solo título.
    Agrupa por identificador de Wikidata (si se conoce), por título normalizado,
    por título original y por títulos que se contienen."""
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
    # 1b) mismo identificador de Wikidata
    por_qid = defaultdict(set)
    for titulo, qid in (qids or {}).items():
        por_qid[qid].add(clave_pelicula(titulo))
    for grupo in por_qid.values():
        g = sorted(c for c in grupo if c in padre)
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


# Orden de preferencia para el póster (las de mejor resolución primero)
PREFERENCIA_POSTER = ["royal_films", "cinepolis", "procinal", "viziona", "cinemark", "cinemateca",
                      "cinemania", "elmuro", "manual", "cine_colombia"]


def elegir_posters(funciones) -> dict[str, str]:
    """Un póster por película, tomado de la cadena con mejor imagen. Quita el campo de cada función."""
    candidatos = defaultdict(dict)
    for f in funciones:
        src = f.pop("poster", "")
        if src:
            candidatos[f["pelicula"]].setdefault(f["fuente"], src)
    return {
        p: next(fuentes[n] for n in sorted(fuentes, key=lambda n: PREFERENCIA_POSTER.index(n)
                                            if n in PREFERENCIA_POSTER else 99))
        for p, fuentes in candidatos.items()
    }


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
                # La hoja manual puede estar vacía sin que sea un error
                estado[nombre] = {"funciones": len(fs),
                                  "error": None if fs or nombre == "manual" else "0 funciones: revisar"}
            except Exception as e:  # una fuente rota no detiene las demás
                traceback.print_exc()
                estado[nombre] = {"funciones": 0, "error": f"{type(e).__name__}: {e}"[:300]}
        navegador.close()

    # Si solo se corrieron algunas fuentes, conserva las funciones de las demás
    if args and anterior:
        funciones += [f for f in anterior.get("funciones", []) if f.get("fuente") not in elegidas]
        estado = {**anterior.get("estado", {}), **estado}

    # Si una fuente falló esta vez (p. ej. un sitio que no responde desde GitHub Actions),
    # se conservan sus funciones anteriores que aún no han pasado, en vez de dejarla vacía.
    ahora = datetime.now(BOGOTA_TZ).isoformat(timespec="seconds")
    for nombre, e in estado.items():
        if e["error"] and nombre in elegidas and anterior:
            viejas = [f for f in anterior.get("funciones", [])
                      if f.get("fuente") == nombre and f.get("hora", "") >= ahora]
            if viejas:
                for f in viejas:
                    f.setdefault("poster", anterior.get("posters", {}).get(f["pelicula"], ""))
                funciones += viejas
                e["conservadas"] = len(viejas)
                print(f"  {nombre}: falló; se conservan {len(viejas)} funciones de la actualización anterior")

    # Quita repetidas (algunas páginas muestran la misma función dos veces)
    vistas, unicas = set(), []
    for f in funciones:
        clave = (f["sala_id"], clave_pelicula(f["pelicula"]), f["hora"], f.get("idioma", ""))
        if clave not in vistas:
            vistas.add(clave)
            unicas.append(f)
    funciones = unicas

    # Alias escritos a mano (scrapers/alias.json) para abreviaturas que no se unen solas
    try:
        alias = json.loads((Path(__file__).parent / "alias.json").read_text(encoding="utf-8"))
        alias = {clave_pelicula(k): v for k, v in alias.items() if not k.startswith("_")}
        for f in funciones:
            f["pelicula"] = alias.get(clave_pelicula(f["pelicula"]), f["pelicula"])
    except (OSError, json.JSONDecodeError):
        pass

    print("→ wikidata")
    try:
        import wikidata
        qids = wikidata.identificar(funciones)
    except Exception as e:  # sin Wikidata se une solo por los nombres
        print(f"  wikidata: {type(e).__name__}: {e}")
        qids = {}
    unificar_titulos(funciones, qids)
    funciones.sort(key=lambda f: (f["hora"], f["sala_id"]))
    mapa_posters = elegir_posters(funciones)
    print(f"  posters: {len(mapa_posters)}/{len({f['pelicula'] for f in funciones})} películas con póster de los cines")
    datos = {"generado": datetime.now(BOGOTA_TZ).isoformat(timespec="seconds"),
             "estado": estado, "posters": mapa_posters, "funciones": funciones}
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\nResumen:")
    for n, e in estado.items():
        extra = f" (se conservaron {e['conservadas']} anteriores)" if e.get("conservadas") else ""
        print(f"  {'✔' if not e['error'] else '✖'} {n}: {e['funciones']} funciones {e['error'] or ''}{extra}")
    print(f"\nGuardado en {SALIDA}")


if __name__ == "__main__":
    main()
