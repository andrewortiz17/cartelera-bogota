# Cartelera Bogotá — borrador v0.1

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
3. Abre la ejecución → sección **Artifacts** → descarga `cartelera-bogota-apk`.
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

## Qué funciona y qué falta

Funciona:
- Mapa con todas las salas, coloreadas por tipo, y filtros por tipo
- Ubicación del usuario (GPS o tocando el mapa) y lista "Cerca de mí" con radio ajustable
- Filtro "solo funciones en la próxima hora"
- Búsqueda de películas, ordenando las salas por cercanía; enlace "Cómo llegar"
- API con carga manual para cineclubes y monitoreo de qué fuente está rota

Falta:
- [ ] Scrapers reales (cada archivo en `backend/app/sources` tiene un TODO con los pasos)
- [ ] Verificar coordenadas y operadores de cada sala (`"verificado": false`)
- [ ] Confirmar Cinema Paraíso y Cine Tonalá (sin dirección actual)
- [ ] Emparejar títulos con TMDB
- [ ] Tiempo de viaje real (OpenRouteService/OSRM) en vez de línea recta
- [ ] Base de datos (Postgres + PostGIS) en lugar de memoria
