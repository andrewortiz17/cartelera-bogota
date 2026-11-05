# BogoCine — borrador v0.2

Cartelera unificada de cadenas, Cinemateca, salas independientes y cineclubes de Bogotá, con mapa y "cines cerca de mí".

## Estructura

```
app/        App Android (Capacitor) — la interfaz está en app/www
  www/data/salas.json   26 salas con tipo, zona y coordenadas (APROXIMADAS, sin verificar)
  android/              Proyecto Android generado, listo para Android Studio
backend/    API FastAPI — un módulo por fuente en backend/app/sources
.github/workflows/build-apk.yml   Compila el APK en GitHub
```

## Obtener el APK

**Opción A — GitHub (sin instalar nada):**
1. Crea un repo en GitHub y sube esta carpeta completa.
2. Pestaña **Actions** → "Compilar APK" se ejecuta solo (≈5 min).
3. Abre la ejecución → sección **Artifacts** → descarga `bogocine-apk`.
4. Pasa `app-debug.apk` al celular e instálalo (permite "orígenes desconocidos").

**Opción B — tu computador:**
```bash
cd app
npm install
npx cap sync android
npx cap open android      # abre Android Studio → Build → Build APK(s)
```
Requiere Android Studio y JDK 21.

## Probar la interfaz sin compilar
```bash
cd app/www && python3 -m http.server 8000   # abrir http://localhost:8000
```

## Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Endpoints: `/salas`, `/funciones`, `/cercanas?lat=&lng=&radio_km=&proxima_hora=`, `/fuentes/estado`,
`POST /admin/funciones` (carga manual, header `x-token`), `POST /admin/actualizar`.

Para que la app use el backend, pon su URL en `app/www/config.js` (`API_URL`) y vuelve a correr `npx cap sync android`.
Mientras `API_URL` esté vacío, la app muestra **horarios inventados** con un aviso.

## Novedades v0.2
- Nuevo nombre e identidad: **BogoCine**, paleta de sala de cine (negro pantalla, rojo telón, latón, crema) y encabezado en forma de claqueta.
- Ícono y pantalla de inicio con claqueta.
- Mapa en escala de grises; cada sala es una casa con un tono de gris según su tipo.
- Con zoom ≥ 16 las casas se convierten en tarjetas con la foto del cine (campo `foto` en `salas.json`).
- Optimización: índices de funciones, eventos delegados, solo se dibuja la vista visible, marcadores reutilizados.

### Fotos de los cines
Solo Andino, Titán Plaza y Unicentro tienen foto (Wikimedia Commons). Para agregar más, pon en `salas.json`:
`"foto": "https://commons.wikimedia.org/wiki/Special:FilePath/NOMBRE_DEL_ARCHIVO.jpg?width=480"` y `"foto_fuente"` con el enlace a la página del archivo.
Antes de publicar la app, revisa el autor y la licencia de cada foto: las licencias CC exigen dar crédito.

## Cartelera real (scrapers)
Los scrapers leen las páginas públicas de cada cadena, igual que lo haría una persona, una vez al día.

| Fuente | Qué lee | Salas |
|---|---|---|
| Cine Colombia | **desactivada**: su web bloquea el acceso automatizado (403). Pendiente de solicitud de datos | 18 |
| Cinemark | página de cada teatro (`cinemark.com.co/ciudad/bogota/<teatro>`) | 8 |
| Procinal | página de cada teatro (`procinal.com.co/ciudad/bogota/teatros/<teatro>`) | 10 |
| Royal Films | página de cada película, por multicine | 5 |
| Cinépolis | cartelera de Bogotá (una página) | 4 |
| Viziona | página principal (una sede, El Edén) | 1 |
| Cinemateca | agenda de cada sede (Centro, El Tunal, Fontanar, CEFE Chapinero) | 4 |

Ojo: Procinal Bogotá está en procinal.com.co; procinal.com es Cineprox, otra empresa que no opera en Bogotá.

**En Windows:**
1. Doble clic en `instalar-scrapers.bat` (una sola vez; necesita Python 3.10+).
2. Doble clic en `actualizar-cartelera.bat`: corre los scrapers, guarda `app/www/data/funciones.json` y lo sube a GitHub.
   Para correr solo una fuente: `actualizar-cartelera.bat cinemark`. Si un sitio bloquea el modo oculto: `python run.py --visible`.
3. Pruebas de los lectores: `cd scrapers` y `python -m pytest pruebas`.

**Que la app vea la cartelera sin recompilar:** si el repo es público, pon en `app/www/config.js`
`FUNCIONES_URL: "https://raw.githubusercontent.com/TU_USUARIO/cartelera-bogota/main/app/www/data/funciones.json"`
y recompila una vez. Desde ahí, cada `actualizar-cartelera.bat` actualiza lo que ve la app.
Sin eso, la app usa la cartelera incluida al compilar (y si ya pasó, la demo).

Si una cadena cambia su página, el resumen del script marca esa fuente con ✖; el lector a ajustar está en `scrapers/fuentes/<cadena>.py`.

## Pósters y unión de películas
- **Pósters:** cada scraper toma la imagen que el propio cine publica junto a cada película
  (`comun.asignar_posters`). Si una película está en varias cadenas, se usa la de mejor resolución.
  Antes de publicar la app con anuncios, pide permiso a las cadenas para mostrar sus pósters.
- **Unión:** las películas se identifican en **Wikidata** (datos CC0, uso comercial permitido) para saber
  cuándo dos cines nombran distinto la misma película; además se une por título original y por
  títulos que se contienen. Caché en `app/www/data/wikidata.json`.
- `scrapers/posters.py` (TMDB) quedó solo para pruebas; no se usa en la cartelera.

## Días siguientes, cineclubes a mano y Google Play

**Varios días:** Cinemark, Procinal, Royal Films, Cinépolis y Viziona se leen hoy y los 2 días
siguientes (pestañas de día de cada web). Si un día no tiene pestaña o la página no cambia al
elegirla, ese día se salta; nunca se copian los horarios de hoy a otro día. Para leer más días:
variable de entorno `BOGOCINE_DIAS` (por defecto 3).

**Cineclubes y salas sin web:** doble clic en `editar-cineclubes.bat`. Abre en Excel
`scrapers/manual.csv` (una fila por función: `sala_id; pelicula; fecha; hora; idioma; formato; url; poster; titulo_original`)
y `scrapers/salas-ids.csv` con los ids válidos. Fecha `20/11/2026` o `2026-11-20`, hora `19:00` o `7:00 pm`.
Guarda como CSV y corre `actualizar-cartelera.bat` (o espera la actualización automática). Las filas
con fecha pasada se ignoran solas.

**Google Play:** todo está en `play-store/` (textos de la ficha y respuestas de seguridad de datos en
`ficha.md`, ícono 512, gráfico 1024×500 y capturas; `tomar-capturas.bat` las regenera). La política
de privacidad está en `docs/` y se publica con GitHub Pages. El AAB firmado sale de Actions →
"Compilar para Google Play" con la llave guardada en los secretos del repositorio.

## Qué funciona y qué falta

Funciona:
- Mapa con todas las salas, coloreadas por tipo, y filtros por tipo
- Ubicación del usuario por GPS y lista "Cerca de mí" con radio ajustable
- Filtro "solo funciones en la próxima hora"
- Búsqueda de películas, ordenando las salas por cercanía; enlace "Cómo llegar"
- API con carga manual para cineclubes y monitoreo de qué fuente está rota

Falta:
- [x] Scrapers de Cine Colombia, Cinemark, Procinal, Royal Films, Cinépolis, Viziona y Cinemateca (`scrapers/`)
- [x] Cineclubes por hoja manual (`scrapers/manual.csv`)
- [x] Selector de días, filtros de idioma y formato, compra por función, cartelera sin internet
- [x] Preparación para Google Play (`play-store/`, `docs/`)
- [ ] Verificar coordenadas y operadores de cada sala (`"verificado": false`)
- [ ] Confirmar Cinema Paraíso y Cine Tonalá (sin dirección actual)
- [x] Unir títulos entre cadenas (normalización + Wikidata) y pósters de los propios cines
- [ ] Tiempo de viaje real (OpenRouteService/OSRM) en vez de línea recta
- [ ] Base de datos (Postgres + PostGIS) en lugar de memoria
