// URL del backend (FastAPI). Vacío = no se usa.
// FUNCIONES_URL: cartelera publicada en internet (p. ej. el funciones.json de tu repo en GitHub).
// Si ambas están vacías, la app usa data/funciones.json incluido al compilar, o la demo.
window.BOGOCINE_CONFIG = {
  API_URL: "",
  // MAPTILER_KEY: opcional. OJO: el plan gratuito de MapTiler no permite uso comercial
  // (con anuncios). Se deja vacío; el mapa principal es OpenFreeMap, que sí lo permite.
  MAPTILER_KEY: "",
  // ESTILO_MAPA: estilo vectorial de OpenFreeMap (dark, positron, bright, liberty, fiord)
  ESTILO_MAPA: "https://tiles.openfreemap.org/styles/dark",
  // CARTO_KEY: opcional. CARTO ya no sirve sin clave.
  CARTO_KEY: "",
  // Página pública de la política de privacidad (GitHub Pages, carpeta docs/)
  PRIVACIDAD_URL: "https://andrewortiz17.github.io/cartelera-bogota/privacidad.html",
  FUNCIONES_URL: "https://raw.githubusercontent.com/andrewortiz17/cartelera-bogota/main/app/www/data/funciones.json"
};
