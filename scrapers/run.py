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
SALIDA = Path(__file__).resolve().parents[1] / "app" / "www" / "data" / "funciones.json"


def unificar_titulos(funciones):
    """La misma película se escribe distinto en cada cadena: usa un solo título."""
    grupos = defaultdict(list)
    for f in funciones:
        grupos[clave_pelicula(f["pelicula"])].append(f)
    for fs in grupos.values():
        # Prefiere el título más común que no esté todo en mayúsculas
        conteo = Counter(f["pelicula"] for f in fs)
        elegido = titulo_bonito(limpiar_titulo(max(conteo, key=lambda t: (not t.isupper(), conteo[t]))))
        original = next((f["titulo_original"] for f in fs if f["titulo_original"]), "")
        for f in fs:
            f["pelicula"] = elegido
            f["titulo_original"] = f["titulo_original"] or original


def main():
    # La consola de Windows no siempre usa UTF-8
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    elegidas = {n: FUENTES[n] for n in args} if args else FUENTES
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

    unificar_titulos(funciones)
    funciones.sort(key=lambda f: (f["hora"], f["sala_id"]))
    datos = {"generado": datetime.now(BOGOTA_TZ).isoformat(timespec="seconds"),
             "estado": estado, "funciones": funciones}
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\nResumen:")
    for n, e in estado.items():
        print(f"  {'✔' if not e['error'] else '✖'} {n}: {e['funciones']} funciones {e['error'] or ''}")
    print(f"\nGuardado en {SALIDA}")


if __name__ == "__main__":
    main()
