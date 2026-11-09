"""Toma las capturas de pantalla para Google Play (1080×1920, como un celular).

Uso (desde la carpeta del proyecto):  python play-store/tomar_capturas.py
o con doble clic en tomar-capturas.bat. Las imágenes quedan en play-store/capturas/.
Usa la cartelera publicada y una ubicación simulada en Chapinero.
"""
import functools
import http.server
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parents[1]
WWW = RAIZ / "app" / "www"
SALIDA = RAIZ / "play-store" / "capturas"
UBICACION = {"latitude": 4.6480, "longitude": -74.0630}   # Chapinero (simulada)
PUERTO = 8765


class Silencioso(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def servidor():
    manejador = functools.partial(Silencioso, directory=str(WWW))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", PUERTO), manejador)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def esperar_mapa(p, ms=4000):
    try:
        p.wait_for_function("document.querySelectorAll('.leaflet-tile-loaded').length > 6", timeout=20000)
    except Exception:
        print("  (el mapa base no terminó de cargar)")
    p.wait_for_timeout(ms)


def esperar_imagenes(p, ms=2500):
    try:
        p.wait_for_function("[...document.images].filter(i => i.offsetParent).every(i => i.complete)", timeout=15000)
    except Exception:
        pass
    p.wait_for_timeout(ms)


def foto(p, nombre):
    destino = SALIDA / nombre
    p.screenshot(path=str(destino))
    print(f"  ✔ {destino.relative_to(RAIZ)}")


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    srv = servidor()
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        ctx = nav.new_context(viewport={"width": 360, "height": 640}, device_scale_factor=3,
                              is_mobile=True, has_touch=True, locale="es-CO",
                              timezone_id="America/Bogota", geolocation=UBICACION,
                              permissions=["geolocation"])
        p = ctx.new_page()
        p.goto(f"http://127.0.0.1:{PUERTO}/", wait_until="domcontentloaded")
        p.wait_for_function("document.querySelectorAll('.marcador-pin').length > 10", timeout=30000)
        p.wait_for_selector("#intro", state="detached", timeout=10000)   # espera que termine la animación de inicio
        p.evaluate("mapa.setView([%f, %f], 13)" % (UBICACION["latitude"], UBICACION["longitude"]))
        esperar_mapa(p)
        foto(p, "01-mapa.png")

        p.click("nav.pestanas button[data-vista=peliculas]")
        p.wait_for_timeout(800)
        if not p.locator("#lista-peliculas [data-peli]").count():
            # De noche ya no quedan funciones de hoy: se muestra la cartelera de mañana
            p.locator("#vista-peliculas .barra-dia .dia").nth(1).click()
            p.wait_for_timeout(800)
        esperar_imagenes(p)
        foto(p, "02-peliculas.png")

        p.click("#lista-peliculas [data-peli]")
        esperar_imagenes(p)
        foto(p, "03-pelicula.png")
        p.click("#hoja-cerrar")

        p.click("nav.pestanas button[data-vista=cerca]")
        esperar_imagenes(p, 1500)
        foto(p, "04-cerca.png")

        # La primera sala cercana que tenga funciones (las de Cine Colombia aún no tienen)
        con_funciones = p.locator("#lista-cerca [data-sala]").filter(has=p.locator("a.hora"))
        (con_funciones if con_funciones.count() else p.locator("#lista-cerca [data-sala]")).first.click()
        esperar_imagenes(p)
        foto(p, "05-sala.png")
        p.click("#hoja-cerrar")

        # Mapa de cerca: los pines se vuelven fotos de los cines
        p.click("nav.pestanas button[data-vista=mapa]")
        p.evaluate("""() => {
            const s = [...state.salaPorId.values()]
              .filter((x) => tieneUbicacion(x) && (state.funcionesPorSala.get(x.id) || []).some(vigente))
              .sort((a, b) => distanciaA(a) - distanciaA(b))[0];
            mapa.setView([s.lat, s.lng], 16);
        }""")
        esperar_mapa(p, 3000)
        esperar_imagenes(p, 1000)
        foto(p, "06-mapa-fotos.png")
        nav.close()
    srv.shutdown()
    print(f"\nListo: {len(list(SALIDA.glob('*.png')))} capturas en {SALIDA}")


if __name__ == "__main__":
    main()
