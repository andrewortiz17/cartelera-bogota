"""Sube a GitHub los cambios del PC sin pelear con la actualización automática.

La cartelera la generan dos lugares (este PC y GitHub Actions), así que funciones.json y
wikidata.json casi siempre chocan al unir. Este script:
  1. guarda en un commit lo que haya cambiado en el PC,
  2. trae lo de GitHub y une,
  3. en los archivos de datos se queda con la cartelera generada más recientemente y
     junta las dos cachés de Wikidata,
  4. sube.
Uso: python scrapers/sincronizar.py "mensaje del commit" [solo-datos]
"""
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
FUNCIONES = "app/www/data/funciones.json"
WIKIDATA = "app/www/data/wikidata.json"
DATOS = [FUNCIONES, WIKIDATA]


def git(*args, check=True) -> subprocess.CompletedProcess:
    r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace")
    salida = (r.stdout + r.stderr).strip()
    if salida:
        print(salida)
    if check and r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} falló (código {r.returncode})")
    return r


def leer_json(texto: str):
    try:
        return json.loads(texto)
    except (json.JSONDecodeError, TypeError):
        return None


def version_remota(ruta: str):
    r = subprocess.run(["git", "show", f"origin/main:{ruta}"], cwd=RAIZ, capture_output=True)
    return leer_json(r.stdout.decode("utf-8", "replace")) if r.returncode == 0 else None


def main():
    mensaje = sys.argv[1] if len(sys.argv) > 1 else "BogoCine: actualizacion"
    solo_datos = "solo-datos" in sys.argv[2:]

    # 1) commit local
    git("add", *(DATOS if solo_datos else ["-A"]), check=False)
    if git("diff", "--cached", "--quiet", check=False).returncode != 0:
        git("commit", "-m", mensaje)
    else:
        print("No hay cambios nuevos en el PC.")

    # 2) traer lo de GitHub y guardar las dos versiones de los datos antes de unir
    git("fetch", "origin")
    locales = {r: leer_json((RAIZ / r).read_text(encoding="utf-8")) if (RAIZ / r).exists() else None for r in DATOS}
    remotos = {r: version_remota(r) for r in DATOS}
    union = git("merge", "--no-edit", "-X", "ours", "origin/main", check=False)
    if union.returncode != 0:
        git("merge", "--abort", check=False)
        raise SystemExit("No se pudo unir con GitHub. Revisa logs y avisa a Claude.")

    # 3) datos: la cartelera más reciente gana; las cachés de Wikidata se juntan
    cambio = False
    loc, rem = locales[FUNCIONES], remotos[FUNCIONES]
    if loc and rem:
        elegida = max((loc, rem), key=lambda d: d.get("generado", ""))
        print(f"Cartelera: se usa la generada el {elegida.get('generado')} "
              f"({'este PC' if elegida is loc else 'GitHub'})")
        (RAIZ / FUNCIONES).write_text(json.dumps(elegida, ensure_ascii=False, indent=1), encoding="utf-8")
        cambio = True
    if isinstance(locales[WIKIDATA], dict) and isinstance(remotos[WIKIDATA], dict):
        juntas = {**remotos[WIKIDATA], **locales[WIKIDATA]}
        (RAIZ / WIKIDATA).write_text(json.dumps(dict(sorted(juntas.items())), ensure_ascii=False, indent=1),
                                     encoding="utf-8")
        cambio = True
    if cambio:
        git("add", *DATOS, check=False)
        if git("diff", "--cached", "--quiet", check=False).returncode != 0:
            git("commit", "-m", "Unir cartelera del PC y de GitHub")

    # 4) subir
    git("push", "origin", "HEAD:main")
    print("Listo: GitHub quedó al día.")


if __name__ == "__main__":
    main()
