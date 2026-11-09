"""Pegar cartelera: convierte el texto copiado de la página de un cine en filas de manual.csv.

Uso: doble clic en pegar-cartelera.bat (o `python scrapers/pegar_cartelera.py`).
  1. Abre la página del cine en tu navegador, como siempre (por ejemplo la de una sala de
     Cine Colombia, en el día que quieras).
  2. Ctrl+A y Ctrl+C para copiar todo el texto de la página.
  3. En esta ventana: pega (Ctrl+V), revisa la sala y la fecha, y presiona "Leer horarios".
  4. Revisa la vista previa (se puede corregir a mano) y presiona "Guardar".
     "Guardar y publicar" además actualiza la cartelera y la sube a GitHub.

Esto solo ordena lo que tú copiaste de una página pública que abriste tú mismo: no entra
a ningún sitio por su cuenta.
"""
import csv
import io
import json
import re
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from comun import hoy, limpiar_lineas, sin_tildes  # noqa: E402
from fuentes import cine_colombia  # noqa: E402

RAIZ = AQUI.parent
MANUAL = AQUI / "manual.csv"
SALAS = json.loads((RAIZ / "app" / "www" / "data" / "salas.json").read_text(encoding="utf-8"))["salas"]
COLUMNAS = ["sala_id", "pelicula", "fecha", "hora", "idioma", "formato", "url", "poster", "titulo_original"]
URL_CC = {v: f"{cine_colombia.BASE}{k}/" for k, v in cine_colombia.SALAS.items()}

RE_HORA = re.compile(r"(\d{1,2}[:.]\d{2})\s*([ap])?\.?\s*m?\.?", re.I)
RE_SOLO_HORAS = re.compile(r"^(\s*\d{1,2}[:.]\d{2}\s*([ap]\.?\s*m\.?)?\s*[-–|·,y/]*)+$", re.I)
NO_TITULO = re.compile(r"^(sala|megasala|dinamix|2d|3d|4dx|imax|doblada|subtitulada|preventa|duraci[oó]n|"
                       r"g[eé]nero|estreno|convenciones|horarios?|comprar|ver |hoy|ma[ñn]ana|auditorio|biblioteca|teatro|"
                       r"lugar|sede|direcci[oó]n|calle |carrera |cra\.? |entrada|\d)", re.I)


# ---------------------------------------------------------------- lógica (sin ventana)

def adivinar_sala(texto: str) -> str | None:
    """Busca el nombre de una sala en las primeras líneas del texto pegado."""
    cabeza = sin_tildes(" ".join(limpiar_lineas(texto)[:40]).lower())
    mejor, largo = None, 0
    for s in SALAS:
        nombre = sin_tildes(s["nombre"].lower())
        for candidato in {nombre, nombre.split(" (")[0], nombre.replace(" plaza", "")}:
            if len(candidato) >= 4 and candidato in cabeza and len(candidato) > largo:
                mejor, largo = s["id"], len(candidato)
    return mejor


def hora_24(texto: str) -> str | None:
    m = RE_HORA.search(texto)
    if not m:
        return None
    h, mi = (int(x) for x in re.split(r"[:.]", m.group(1)))
    ap = (m.group(2) or "").lower()
    if ap == "p" and h != 12:
        h += 12
    if ap == "a" and h == 12:
        h = 0
    return f"{h:02d}:{mi:02d}" if h < 24 and mi < 60 else None


def leer_generico(texto: str, sala_id: str, dia: date) -> list[dict]:
    """Para cualquier página: cada hora se asigna al último renglón que parece un título."""
    filas, titulo = [], None
    for l in limpiar_lineas(texto):
        if RE_SOLO_HORAS.match(l):
            if titulo:
                for m in RE_HORA.finditer(l):
                    h = hora_24(m.group(0))
                    if h:
                        filas.append(fila(sala_id, titulo, dia, h))
        elif 2 <= len(l) <= 80 and not NO_TITULO.match(l):
            titulo = l
    return filas


def leer_cine_colombia(texto: str, sala_id: str, dia: date) -> list[dict]:
    filas = []
    for f in cine_colombia.parsear(texto, sala_id, URL_CC.get(sala_id, ""), dia):
        momento = datetime.fromisoformat(f.hora)
        filas.append(fila(sala_id, f.pelicula, momento.date(), momento.strftime("%H:%M"),
                          formato=f.formato, url=f.url_compra, original=f.titulo_original))
    return filas


def fila(sala_id, pelicula, dia, hora, idioma="", formato="", url="", original=""):
    return {"sala_id": sala_id, "pelicula": pelicula.strip(), "fecha": dia.strftime("%d/%m/%Y"),
            "hora": hora, "idioma": idioma, "formato": formato, "url": url or URL_CC.get(sala_id, ""),
            "poster": "", "titulo_original": original}


def leer(texto: str, sala_id: str, dia: date, tipo: str = "auto") -> list[dict]:
    if tipo == "cine_colombia" or (tipo == "auto" and sala_id.startswith("cc-")):
        filas = leer_cine_colombia(texto, sala_id, dia)
        if filas or tipo == "cine_colombia":
            return filas
    return leer_generico(texto, sala_id, dia)


def a_texto(filas: list[dict]) -> str:
    salida = io.StringIO()
    w = csv.DictWriter(salida, fieldnames=COLUMNAS, delimiter=";", lineterminator="\n")
    w.writerows(filas)
    return salida.getvalue()


def de_texto(texto: str) -> list[dict]:
    return [dict(zip(COLUMNAS, (c.strip() for c in r))) for r in csv.reader(io.StringIO(texto), delimiter=";")
            if r and any(c.strip() for c in r)]


def guardar(filas: list[dict]) -> int:
    """Agrega las filas a manual.csv. Si ya había filas de la misma sala y fecha, las reemplaza
    (así se puede volver a pegar el mismo día sin duplicar). También borra las de días pasados."""
    existentes = []
    if MANUAL.exists():
        texto = MANUAL.read_bytes().decode("utf-8-sig", errors="replace")
        sep = ";" if texto.splitlines()[0].count(";") >= texto.splitlines()[0].count(",") else ","
        existentes = list(csv.DictReader(io.StringIO(texto), delimiter=sep))
    nuevas = {(f["sala_id"], f["fecha"]) for f in filas}

    def vigente(f):
        try:
            d = datetime.strptime(f.get("fecha", ""), "%d/%m/%Y").date()
        except ValueError:
            try:
                d = date.fromisoformat(f.get("fecha", ""))
            except ValueError:
                return True
        return d >= hoy()

    quedan = [f for f in existentes if (f.get("sala_id"), f.get("fecha")) not in nuevas and vigente(f)]
    with open(MANUAL, "w", encoding="utf-8-sig", newline="") as fh:   # utf-8-sig: Excel lo abre bien
        w = csv.DictWriter(fh, fieldnames=COLUMNAS, delimiter=";", lineterminator="\r\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(quedan + filas)
    return len(quedan) + len(filas)


# ---------------------------------------------------------------- ventana

def ventana():
    import tkinter as tk
    from tkinter import messagebox, scrolledtext, ttk

    raiz = tk.Tk()
    raiz.title("BogoCine · Pegar cartelera")
    raiz.geometry("980x720")
    raiz.configure(bg="#0d0c0b")
    estilo = ttk.Style()
    estilo.theme_use("clam")
    for w in ("TLabel", "TFrame"):
        estilo.configure(w, background="#0d0c0b", foreground="#f3ead8")
    estilo.configure("TButton", padding=6)

    opciones = [f'{s["nombre"]}  ·  {s["operador"]}  [{s["id"]}]' for s in SALAS]
    dias = [hoy() + timedelta(days=k) for k in range(8)]
    nombres_dia = ["Hoy", "Mañana"] + [d.strftime("%A") for d in dias[2:]]
    etiquetas_dia = [f"{n} {d:%d/%m/%Y}" for n, d in zip(nombres_dia, dias)]

    arriba = ttk.Frame(raiz, padding=10)
    arriba.pack(fill="x")
    ttk.Label(arriba, text="Sala:").grid(row=0, column=0, sticky="w")
    sala = ttk.Combobox(arriba, values=opciones, width=70, state="readonly")
    sala.grid(row=0, column=1, sticky="w", padx=6)
    ttk.Label(arriba, text="Fecha:").grid(row=0, column=2, sticky="w", padx=(16, 0))
    fecha = ttk.Combobox(arriba, values=etiquetas_dia, width=20, state="readonly")
    fecha.current(0)
    fecha.grid(row=0, column=3, sticky="w", padx=6)
    ttk.Label(arriba, text="Formato de la página:").grid(row=1, column=0, sticky="w", pady=(8, 0))
    tipo = ttk.Combobox(arriba, values=["Detectar solo", "Cine Colombia", "Otra página (genérico)"],
                        width=30, state="readonly")
    tipo.current(0)
    tipo.grid(row=1, column=1, sticky="w", padx=6, pady=(8, 0))

    ttk.Label(raiz, text="1) Pega aquí el texto de la página del cine (Ctrl+A y Ctrl+C en el navegador, Ctrl+V aquí):",
              padding=(10, 4)).pack(anchor="w")
    entrada = scrolledtext.ScrolledText(raiz, height=14, bg="#181614", fg="#f3ead8", insertbackground="#f3ead8")
    entrada.pack(fill="both", expand=True, padx=10)

    medio = ttk.Frame(raiz, padding=10)
    medio.pack(fill="x")
    aviso = ttk.Label(medio, text="")
    vista = None

    def id_sala():
        v = sala.get()
        return v[v.rfind("[") + 1:-1] if v else ""

    def al_pegar(_=None):
        raiz.after(50, lambda: (not sala.get()) and detectar())

    def detectar():
        sid = adivinar_sala(entrada.get("1.0", "end"))
        if sid:
            sala.current([s["id"] for s in SALAS].index(sid))

    def leer_horarios():
        if not id_sala():
            detectar()
        if not id_sala():
            messagebox.showwarning("Falta la sala", "Elige la sala a la que corresponde el texto.")
            return
        modo = {0: "auto", 1: "cine_colombia", 2: "generico"}[tipo.current()]
        filas = leer(entrada.get("1.0", "end"), id_sala(), dias[fecha.current()], modo)
        vista.delete("1.0", "end")
        vista.insert("1.0", a_texto(filas))
        peliculas = len({f["pelicula"] for f in filas})
        aviso.config(text=f"{len(filas)} funciones de {peliculas} películas. Revisa y corrige si hace falta.")

    def guardar_filas(publicar=False):
        filas = de_texto(vista.get("1.0", "end"))
        if not filas:
            messagebox.showwarning("Nada que guardar", "Primero presiona «Leer horarios».")
            return
        total = guardar(filas)
        entrada.delete("1.0", "end")
        vista.delete("1.0", "end")
        aviso.config(text=f"Guardadas {len(filas)} funciones. manual.csv tiene {total} filas.")
        if publicar:
            publicar_ahora()

    def publicar_ahora():
        aviso.config(text="Actualizando y subiendo a GitHub… (tarda menos de un minuto)")
        raiz.update()
        py = sys.executable
        r1 = subprocess.run([py, "-u", "run.py", "manual"], cwd=AQUI, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
        r2 = subprocess.run([py, "-u", "sincronizar.py", "Cartelera manual", "solo-datos"], cwd=AQUI,
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
        log = RAIZ / "logs" / "pegar.txt"
        log.parent.mkdir(exist_ok=True)
        log.write_text(r1.stdout + r1.stderr + "\n" + r2.stdout + r2.stderr, encoding="utf-8")
        if r1.returncode == 0 and r2.returncode == 0:
            aviso.config(text="Listo: la cartelera quedó publicada.")
        else:
            aviso.config(text="Algo falló al publicar; revisa logs\\pegar.txt")

    ttk.Button(medio, text="Detectar sala", command=detectar).pack(side="left")
    ttk.Button(medio, text="2) Leer horarios", command=leer_horarios).pack(side="left", padx=8)
    aviso.pack(side="left", padx=8)

    ttk.Label(raiz, text="3) Vista previa (sala_id; película; fecha; hora; idioma; formato; url; póster; título original):",
              padding=(10, 4)).pack(anchor="w")
    vista = scrolledtext.ScrolledText(raiz, height=12, bg="#181614", fg="#d6a649", insertbackground="#f3ead8")
    vista.pack(fill="both", expand=True, padx=10)

    abajo = ttk.Frame(raiz, padding=10)
    abajo.pack(fill="x")
    ttk.Button(abajo, text="4) Guardar en manual.csv", command=guardar_filas).pack(side="left")
    ttk.Button(abajo, text="Guardar y publicar", command=lambda: guardar_filas(True)).pack(side="left", padx=8)

    entrada.bind("<<Paste>>", al_pegar)
    entrada.focus_set()
    raiz.mainloop()


if __name__ == "__main__":
    ventana()
