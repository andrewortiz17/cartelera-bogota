"""Pruebas de los lectores con texto real copiado de cada sitio (4 nov 2026).
Ejecutar desde scrapers/:  python -m pytest pruebas   (o: python pruebas/test_parsers.py)
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fuentes import cine_colombia, cinemark, cinemateca, cinepolis, procinal, royal_films, viziona  # noqa: E402

DIA = date(2026, 11, 4)

CINE_COLOMBIA = """Cine Colombia
TITAN PLAZA
Carrera 72 # 80 - 94
Horarios
HOY
JUE
5
NOV
Preventa
Godzilla Minus Zero
Godzilla Minus Zero
Recomendada para Mayores de 12 años
Duración
2h 15m
Estreno: 2026-11-05
Género: Acción
Convenciones
ㅤ
Todos los horarios:
12:40P.M.
SALA 3
3:30P.M.
SALA 3
9:45P.M.
SALA 3
Heart of the Beast
El Corazón de la Bestia
Recomendada para Mayores de 12 años
Duración
1h 41m
Estreno: 2026-09-24
Género: Suspenso
Convenciones
ㅤ
Todos los horarios:
2:00P.M.
DINAMIX
9:30P.M.
DINAMIX
Tadeo Jones y la lámpara maravillosa
Para todo el Público
Duración
1h 34m
Estreno: 2026-10-08
Género: Animación
Convenciones
ㅤ
1:10P.M.
SALA 1
"""

CINEMARK = """USTED ESTÁ EN:
Bogota
Plaza Imperial
CARGANDO
CLAYFACE
VER DETALLE
TERROR+ 15 AÑOS110 MINUTOS
HORARIOS DISPONIBLES
* Los horarios aquí expuestos representan el inicio de cada función
2D
DOBLADA
Sillas:
GENERAL
14:35
17:45
21:10
CARGANDO
SHREK RE
VER DETALLE
ANIMACIÓNTODOS90 MINUTOS
HORARIOS DISPONIBLES
2D
DOBLADA
Sillas:
GENERAL
15:45
"""

ROYAL = """Inicio   /   LA EXORCISTA
LA EXORCISTA
ESPAÑOL (LATINOAMERICA)
TERROR | THRILLER
2D
85 mins
Nombre original: THE CONTAINMENT
Clasificación: Para mayores de 15 años
slide 1 of 1
MIÉ
04 nov
Multicine Paseo Villa Del Rio
2D - ORI
09:10 p. m.
JUE
05 nov
Multicine Paseo Villa Del Rio
2D - ORI
06:00 p. m.
CARTELERA BOGOTÁ
"""

CINEPOLIS = """Selecciona un cine
Cinépolis Diverplaza
Cinépolis VIP Plaza Claro
Idioma
DOBLADA
CINÉPOLIS VIP PLAZA CLARO
?
Clayface
A15108 min
DOB
15:4018:20
DIG
SUB
21:20
Godzilla Minus Zero
A12135 min
DOB
15:0018:3022:00
RE: Cars una aventura sobre ruedas
TP116 min
DOB
16:0019:00
"""

CINEMATECA = """HOY
CINE
Estrenos Internacionales
RESURECCIÓN
SALA 3
Noviembre 18
6:30 pm
Estrenos Nacionales
KMKZ: SALVAJE, LIBRE Y VALIENTE
SALA CAPITAL
Noviembre 18
8:00 pm
Estrenos Internacionales
ENGENDRO
SALA CAPITAL
Noviembre 2
2:00 pm
"""

PROCINAL = """Selecciona el día de tu función
Mie, Nov 4 2026
Jue, Nov 5 2026
GODZILLA MINUS ZERO
GODZILLA MINUS ZERO
Subtitulada - 2D
6:30 pm
9:10 pm
REESTRENO - SHREK
SHREK
Doblada - 2D
2:00 pm
SENSATEZ Y SENTIMIENTO
SENSE AND SENSIBILITY
Doblada - 2D
2:40 pm
Subtitulada - 2D
8:40 pm
Salitre Plaza
Cra. 68b #24-39
Descarga el app en:
"""

VIZIONA = """Elige la fecha de tu función:
Mie
Nov 4 2026
CLAYFACE
Sala: VMAX
2D
DOBLADA
3:15 pm
5:45 pm
Sala: VIP
2D
DOBLADA
6:55 pm
EL DESPERTAR
Sala: GE Y VIP
2D
ORIGINAL
8:55 pm
"""


def test_cine_colombia():
    fs = cine_colombia.parsear(CINE_COLOMBIA, "cc-titan", "u", DIA)
    assert len(fs) == 6
    assert fs[0].pelicula == "Godzilla Minus Zero" and fs[0].hora == "2026-11-04T12:40:00-05:00"
    assert fs[0].formato == "Sala 3" and fs[0].duracion_min == 135
    bestia = [f for f in fs if f.pelicula == "El Corazón de la Bestia"]
    assert len(bestia) == 2 and bestia[0].titulo_original == "Heart of the Beast"
    assert bestia[1].hora == "2026-11-04T21:30:00-05:00"
    assert any(f.pelicula == "Tadeo Jones y la lámpara maravillosa" for f in fs)


def test_cinemark():
    fs = cinemark.parsear(CINEMARK, "cm-plaza-imperial", "u", DIA)
    assert [f.hora[11:16] for f in fs] == ["14:35", "17:45", "21:10", "15:45"]
    assert fs[0].pelicula == "Clayface" and fs[0].idioma == "Doblada" and fs[0].formato == "2D"
    assert fs[0].duracion_min == 110 and fs[3].pelicula == "Shrek re"


def test_royal_films():
    fs = royal_films.parsear(ROYAL, "u", DIA)
    assert len(fs) == 1  # solo hoy
    f = fs[0]
    assert f.sala_id == "rf-villa-del-rio" and f.hora == "2026-11-04T21:10:00-05:00"
    assert f.pelicula == "La exorcista" and f.idioma == "Subtitulada" and f.duracion_min == 85


def test_cinepolis():
    fs = cinepolis.parsear(CINEPOLIS, DIA)
    assert all(f.sala_id == "cp-plaza-claro" for f in fs)
    clay = [f for f in fs if f.pelicula == "Clayface"]
    assert [(f.hora[11:16], f.idioma) for f in clay] == [("15:40", "Doblada"), ("18:20", "Doblada"), ("21:20", "Subtitulada")]
    assert len([f for f in fs if f.pelicula == "Godzilla Minus Zero"]) == 3
    assert clay[0].clasificacion == "A15" and clay[0].duracion_min == 108


def test_cinemateca():
    fs = cinemateca.parsear(CINEMATECA, "cine-cinemateca", "u", DIA)
    assert len(fs) == 2  # la del 2 de noviembre ya pasó
    assert fs[0].pelicula == "Resurección" and fs[0].hora == "2026-11-18T18:30:00-05:00"
    assert fs[1].formato == "Sala Capital"


def test_procinal():
    fs = procinal.parsear(PROCINAL, "pr-salitre", "u", DIA)
    assert len(fs) == 5
    assert fs[0].pelicula == "Godzilla minus zero" and fs[0].idioma == "Subtitulada" and fs[0].hora[11:16] == "18:30"
    sens = [f for f in fs if f.pelicula.startswith("Sensatez")]
    assert [(f.idioma, f.hora[11:16]) for f in sens] == [("Doblada", "14:40"), ("Subtitulada", "20:40")]
    assert sens[0].titulo_original == "Sense and sensibility"


def test_viziona():
    fs = viziona.parsear(VIZIONA, DIA)
    assert [(f.pelicula, f.formato, f.hora[11:16]) for f in fs] == [
        ("Clayface", "2D Vmax", "15:15"), ("Clayface", "2D Vmax", "17:45"),
        ("Clayface", "2D Vip", "18:55"), ("El despertar", "2D Ge Y Vip", "20:55")]
    assert fs[-1].idioma == "Original"


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
            print("✔", nombre)
