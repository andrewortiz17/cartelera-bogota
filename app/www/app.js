/* Animación de inicio: se retira sola a los ~1,6 s, o antes si se toca la pantalla */
(function intro() {
  const el = document.getElementById("intro");
  if (!el) return;
  const quieto = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const cerrar = () => { el.classList.add("fuera"); setTimeout(() => el.remove(), 400); };
  setTimeout(cerrar, quieto ? 500 : 1650);
  el.addEventListener("click", cerrar, { once: true });
})();

/* BogoCine — v0.3
   Mapa en grises con casas por tipo de sala; al acercarse (zoom ≥ 16) cada casa
   se convierte en la foto del cine. "Cerca de mí" y búsqueda por película.
   Sin backend configurado usa horarios de demostración. */
"use strict";

const BOGOTA = { lat: 4.6533, lng: -74.0836 };
const ZOOM_FOTOS = 16;
const TIPO = {
  cadena: "Cadena", cinemateca: "Cinemateca",
  independiente: "Independiente", cineclub: "Cineclub",
};
const GRIS = {
  cadena: "#f4f4f2", cinemateca: "#c8c8c5",
  independiente: "#9a9a97", cineclub: "#6c6c69",
};

const $ = (id) => document.getElementById(id);
const state = {
  posters: {},                   // título → url del póster (publicado por el cine)
  salas: [],
  salaPorId: new Map(),
  funcionesPorSala: new Map(),   // índice sala_id → funciones ordenadas
  funcionesPorPeli: new Map(),   // índice película → funciones
  user: null,
  tipos: new Set(Object.keys(TIPO)),
  radioKm: 5,
  dia: null,                     // inicio (00:00) del día elegido; null = hoy
  idioma: "",                    // "", "Doblada", "Subtitulada", "Original", "Español"
  formato: "",                   // "", "2D", "3D", "IMAX", "VIP"…
  soloProximaHora: false,
  busqueda: "",
  vista: "mapa",
  demo: false,
};

/* ================= Utilidades ================= */

function distanciaKm(a, b) { // Haversine
  const R = 6371, r = (x) => (x * Math.PI) / 180;
  const h = Math.sin(r(b.lat - a.lat) / 2) ** 2 +
    Math.cos(r(a.lat)) * Math.cos(r(b.lat)) * Math.sin(r(b.lng - a.lng) / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}
const fmtKm = (km) => (km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(1)} km`);
const fmtHora = (d) => d.toLocaleTimeString("es-CO", { hour: "numeric", minute: "2-digit" }).replace(/\s/g, " ");
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const tieneUbicacion = (s) => Number.isFinite(s.lat) && Number.isFinite(s.lng);
const minutosHasta = (d) => (d - Date.now()) / 60000;
const enProximaHora = (d) => { const m = minutosHasta(d); return m >= 0 && m <= 60; };
// Un "día de cine" va de las 4 a. m. a las 4 a. m. del día siguiente (por las funciones de trasnoche).
function diaDeCine(fecha) {
  const d = new Date(fecha);
  if (d.getHours() < 4) d.setDate(d.getDate() - 1);
  d.setHours(0, 0, 0, 0);
  return d;
}
const hoyCine = () => diaDeCine(new Date());
const diaElegido = () => state.dia || hoyCine();
const esHoy = () => diaElegido().getTime() === hoyCine().getTime();
function ventanaDia() {
  const ini = new Date(diaElegido()); ini.setHours(4, 0, 0, 0);
  const fin = new Date(ini); fin.setDate(fin.getDate() + 1);
  return [ini, fin];
}
const FORMATOS = ["IMAX", "4DX", "3D", "XD", "VIP", "DBOX", "MACRO XE", "2D"];
function pasaFiltros(f) {
  if (state.idioma && !(f.idioma || "").toLowerCase().startsWith(state.idioma.toLowerCase())) return false;
  if (state.formato && !(f.formato || "").toUpperCase().includes(state.formato)) return false;
  return true;
}
function vigente(f) {
  const [ini, fin] = ventanaDia();
  if (f.hora >= fin || f.hora < ini) return false;
  if (esHoy() && minutosHasta(f.hora) < -10) return false;
  return pasaFiltros(f);
}
const distanciaA = (s) => (state.user && tieneUbicacion(s) ? distanciaKm(state.user, s) : null);
const visible = (s) => state.tipos.has(s.tipo);
function debounce(fn, ms) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }

// Pin de cine: gota en el tono de gris del tipo de sala, con una claqueta adentro
const svgPin = (color, w = 30) => `
  <svg width="${w}" height="${w * 4 / 3}" viewBox="0 0 30 40" aria-hidden="true">
    <path d="M15 38.5S3 24.5 3 14a12 12 0 0 1 24 0c0 10.5-12 24.5-12 24.5Z" fill="${color}" stroke="#0d0c0b" stroke-width="2" stroke-linejoin="round"/>
    <rect x="8.5" y="12.6" width="13" height="8.4" rx="1.2" fill="#0d0c0b"/>
    <path d="M8.3 11.4 20.9 8.1l.7 2.6L9 14Z" fill="#0d0c0b"/>
    <path d="M11.2 12.9 13 10.1M14.6 12 16.4 9.2M18 11.1l1.8-2.8" stroke="${color}" stroke-width="1.3" stroke-linecap="round"/>
    <path d="M10.5 16.8h9" stroke="${color}" stroke-width="1" opacity=".7"/>
  </svg>`;

// Pin con el logo de la cadena o sala (su ícono de pestaña del navegador) en un círculo
const svgGota = (color, w) => `
  <svg width="${w}" height="${w * 4 / 3}" viewBox="0 0 30 40" aria-hidden="true">
    <path d="M15 38.5S3 24.5 3 14a12 12 0 0 1 24 0c0 10.5-12 24.5-12 24.5Z" fill="${color}" stroke="#0d0c0b" stroke-width="2" stroke-linejoin="round"/>
    <circle cx="15" cy="14" r="9.6" fill="#f3ead8"/>
  </svg>`;
function pinSala(s, w = 30) {
  if (!s.logo) return svgPin(GRIS[s.tipo], w);
  return `<span class="pin-logo" style="width:${w}px;height:${w * 4 / 3}px">${svgGota(GRIS[s.tipo], w)}` +
    `<img src="img/logos/${esc(s.logo)}" alt="" loading="lazy" style="width:${Math.round(w * .6)}px;height:${Math.round(w * .6)}px;top:${Math.round(w * 4 / 3 * 14 / 40)}px"></span>`;
}

/* ================= Datos ================= */

async function cargarDatos() {
  const cfg = window.BOGOCINE_CONFIG || {};
  let salas, funciones;
  if (cfg.API_URL) {
    try {
      [salas, funciones] = await Promise.all([
        fetch(`${cfg.API_URL}/salas`).then((r) => r.json()),
        fetch(`${cfg.API_URL}/funciones`).then((r) => r.json()),
      ]);
    } catch (e) {
      console.warn("Backend no disponible", e);
    }
  }
  if (!salas) salas = (await fetch("data/salas.json").then((r) => r.json())).salas;

  // Cartelera generada por los scrapers: la de internet; si no hay conexión, la guardada en el
  // celular la última vez; si tampoco, la incluida en la app.
  const usar = (datos, origen) => {
    funciones = datos.funciones;
    state.generado = datos.generado ? new Date(datos.generado) : null;
    state.posters = datos.posters || {};
    state.origen = origen;
  };
  if (!funciones && cfg.FUNCIONES_URL) {
    try {
      const ctrl = new AbortController();
      const corte = setTimeout(() => ctrl.abort(), 8000);
      const texto = await fetch(cfg.FUNCIONES_URL, { cache: "no-store", signal: ctrl.signal }).then((r) => (r.ok ? r.text() : null));
      clearTimeout(corte);
      const datos = texto && JSON.parse(texto);
      if (datos?.funciones?.length) {
        usar(datos, "internet");
        try { localStorage.setItem("bogocine_cartelera", texto); } catch { /* sin espacio o sin permiso */ }
      }
    } catch { /* sin conexión */ }
  }
  if (!funciones) {
    try {
      const guardada = JSON.parse(localStorage.getItem("bogocine_cartelera") || "null");
      if (guardada?.funciones?.length) usar(guardada, "guardada");
    } catch { /* caché dañada o no disponible */ }
  }
  if (!funciones) {
    try {
      const datos = await fetch("data/funciones.json", { cache: "no-store" }).then((r) => (r.ok ? r.json() : null));
      if (datos?.funciones?.length) usar(datos, "incluida");
    } catch { /* no viene en la app */ }
  }
  if (funciones) {
    funciones = funciones.map((f) => ({ ...f, hora: new Date(f.hora) }));
    // Si la cartelera es vieja (nada vigente), mejor mostrar la demo que una app vacía
    if (!funciones.some((f) => minutosHasta(f.hora) > -24 * 60)) funciones = null;
  }
  if (!funciones) {
    funciones = generarDemo(salas);
    state.demo = true;
  }
  state.salas = salas;
  state.salaPorId = new Map(salas.map((s) => [s.id, s]));
  indexar(funciones);
}

function indexar(funciones) {
  funciones.sort((a, b) => a.hora - b.hora);
  state.funcionesPorSala.clear(); state.funcionesPorPeli.clear();
  for (const f of funciones) {
    if (!state.funcionesPorSala.has(f.sala_id)) state.funcionesPorSala.set(f.sala_id, []);
    state.funcionesPorSala.get(f.sala_id).push(f);
    if (!state.funcionesPorPeli.has(f.pelicula)) state.funcionesPorPeli.set(f.pelicula, []);
    state.funcionesPorPeli.get(f.pelicula).push(f);
  }
}

// Horarios inventados para probar la interfaz (títulos ficticios)
function generarDemo(salas) {
  const comerciales = ["El último tren a Zipaquirá", "Galaxia rota", "Monstruos del páramo",
    "Operación Andes", "La casa del río", "Pequeños héroes 3"];
  const arte = ["Niebla en La Candelaria", "Retrato de un silencio", "Ciclo: cine colombiano de los 80",
    "Memoria del agua (documental)", "Cortos universitarios", "Noche negra (restaurada)"];
  const formatos = ["2D", "3D", "IMAX", "XD"];
  let seed = 11; const rnd = () => ((seed = (seed * 9301 + 49297) % 233280) / 233280);
  const base = new Date(); base.setSeconds(0, 0);
  const out = [];
  for (const s of salas) {
    const cadena = s.tipo === "cadena";
    const lista = cadena ? comerciales : arte;
    const n = cadena ? 12 : 2 + Math.floor(rnd() * 2);
    for (let i = 0; i < n; i++) {
      const d = new Date(base);
      d.setHours(cadena ? 11 + Math.floor(rnd() * 12) : 14 + Math.floor(rnd() * 7), [0, 15, 30, 45][Math.floor(rnd() * 4)]);
      out.push({
        sala_id: s.id, pelicula: lista[Math.floor(rnd() * lista.length)], hora: d,
        formato: cadena ? formatos[Math.floor(rnd() * 4)] : "",
      });
    }
  }
  return out;
}

/* ================= Mapa ================= */

const mapa = L.map("mapa", { zoomControl: false, attributionControl: true })
  .setView([BOGOTA.lat, BOGOTA.lng], 12);
// Mapa base: se prueban proveedores en orden y se cambia al siguiente si las teselas no cargan.
// Con MAPTILER_KEY en config.js se usa primero MapTiler (requiere API key gratuita).
const CFG_MAPA = window.BOGOCINE_CONFIG || {};
const ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/";
const PROVEEDORES = [
  ...(CFG_MAPA.MAPTILER_KEY ? [{
    nombre: "MapTiler",
    url: `https://api.maptiler.com/maps/dataviz-dark/256/{z}/{x}/{y}.png?key=${CFG_MAPA.MAPTILER_KEY}`,
    opciones: { attribution: '<a href="https://www.maptiler.com/copyright/" target="_blank" rel="noopener">© MapTiler</a> <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">© OpenStreetMap</a>' },
    logo: true,   // el plan gratuito de MapTiler exige mostrar su logo
  }] : []),
  // Esri: gris oscuro, sin clave. Las calles y barrios van en una capa de etiquetas aparte.
  { nombre: "Esri", url: ESRI + "World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
    etiquetas: ESRI + "World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}",
    opciones: { maxNativeZoom: 16, attribution: "Mapa © Esri, HERE, Garmin, © OpenStreetMap" } },
  // CARTO ahora exige clave: sin ella entrega teselas con el aviso "API KEY REQUIRED"
  ...(CFG_MAPA.CARTO_KEY ? [{
    nombre: "CARTO", url: `https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png?api_key=${CFG_MAPA.CARTO_KEY}`,
    opciones: { subdomains: "abcd", attribution: "© OpenStreetMap · © CARTO" } }] : []),
  { nombre: "OpenStreetMap", url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    opciones: { attribution: "© OpenStreetMap" }, claro: true },
];
let capaBase = null, capaEtiquetas = null, indiceProveedor = -1;

function usarProveedor(n) {
  if (n >= PROVEEDORES.length) { indiceProveedor = n; $("aviso-mapa").hidden = false; return; }
  const p = PROVEEDORES[n];
  indiceProveedor = n;
  if (capaBase) capaBase.remove();
  if (capaEtiquetas) { capaEtiquetas.remove(); capaEtiquetas = null; }
  let cargadas = 0, errores = 0;
  capaBase = L.tileLayer(p.url, { maxZoom: 19, ...p.opciones }).addTo(mapa);
  document.getElementById("logo-maptiler")?.toggleAttribute("hidden", !p.logo);
  if (p.etiquetas) {
    capaEtiquetas = L.tileLayer(p.etiquetas, { maxZoom: 19, maxNativeZoom: 16, pane: "overlayPane", opacity: 0.85 }).addTo(mapa);
  }
  document.getElementById("mapa").classList.toggle("mapa-claro", !!p.claro);
  capaBase.on("tileload", () => { cargadas++; $("aviso-mapa").hidden = true; });
  capaBase.on("tileerror", () => {
    // Si fallan varias teselas antes de que cargue alguna, pasa al siguiente proveedor
    if (++errores >= 4 && cargadas === 0 && indiceProveedor === n) {
      console.warn(`Mapa: ${p.nombre} no responde, probando el siguiente`);
      usarProveedor(n + 1);
    }
  });
}
// Algunos proveedores responden con una imagen de error ("API KEY REQUIRED", "Invalid key")
// en vez de fallar, y el mapa no se entera. Antes de usar uno, se prueba una tesela.
async function teselaValida(p) {
  const url = p.url.replace("{s}", "a").replace("{z}", "12").replace("{x}", "1203")
    .replace("{y}", "1986").replace("{r}", "");
  try {
    const r = await fetch(url, { mode: "cors", cache: "no-store" });
    return r.ok;
  } catch {
    return true;   // si el navegador no deja leer la respuesta, se confía en el aviso de error de Leaflet
  }
}
(async () => {
  for (let n = 0; n < PROVEEDORES.length; n++) {
    if (await teselaValida(PROVEEDORES[n])) { usarProveedor(n); return; }
    console.warn(`Mapa: ${PROVEEDORES[n].nombre} rechazó la tesela de prueba`);
  }
  usarProveedor(PROVEEDORES.length);
})();

const marcadores = new Map(); // sala_id → L.Marker (se crean una sola vez)
let modoFoto = null;

function iconoCasa(s) {
  const w = s.logo ? 34 : 30;   // los pines con logo son un poco más grandes para que se lea
  const [dx] = corrimiento(s.id, w * 0.8, 0, false);
  return L.divIcon({ className: "marcador-pin", html: pinSala(s, w), iconSize: [w, w * 4 / 3], iconAnchor: [w / 2 - dx, w * 4 / 3 - 1] });
}
function iconoFoto(s) {
  const [dx, dy] = corrimiento(s.id, 140, 126, true);
  // Con foto: imagen de fondo. Sin foto: casa ilustrada en el tono de su tipo
  const bg = s.foto ? ` style="background-image:url('${esc(s.foto)}')"` : "";
  const img = `<div class="mf-img"${bg}>${s.foto ? "" : pinSala(s, 30)}</div>`;
  return L.divIcon({
    className: "marcador-foto",
    html: `<div class="mf-franjas"></div>${img}<div class="mf-nombre">${s.logo ? `<img class="mf-logo" src="img/logos/${esc(s.logo)}" alt="">` : `<i style="background:${GRIS[s.tipo]}"></i>`}${esc(s.nombre)}</div>`,
    iconSize: [132, 118], iconAnchor: [66 - dx, 118 - dy],
  });
}

// Salas en el mismo centro comercial (a menos de 80 m): se reparten a los lados para que
// no queden una encima de otra. desplazamiento = posición dentro del grupo, centrada en 0.
const desplazamiento = new Map();
const centroComercial = (s) => (/C\.C\. ([^,]+)/.exec(s.zona || "") || [])[1] || "";
// Corrimiento en píxeles: en fila para los pines; en cuadrícula de 2 columnas para las fotos
function corrimiento(id, ancho, alto, cuadricula) {
  const d = desplazamiento.get(id);
  if (!d || d.n < 2) return [0, 0];
  if (!cuadricula || d.n === 2) return [(d.k - (d.n - 1) / 2) * ancho, 0];
  return [((d.k % 2) - 0.5) * ancho, -Math.floor(d.k / 2) * alto];
}
function agruparCercanas() {
  const conUbic = state.salas.filter(tieneUbicacion);
  const usados = new Set();
  for (const s of conUbic) {
    if (usados.has(s.id)) continue;
    const grupo = conUbic.filter((o) => !usados.has(o.id) && (distanciaKm(s, o) < 0.08 ||
      (centroComercial(s) && centroComercial(s) === centroComercial(o))));
    // Centro del grupo: en modo foto todas las tarjetas se ordenan alrededor de ese punto
    const lat = grupo.reduce((t, o) => t + o.lat, 0) / grupo.length;
    const lng = grupo.reduce((t, o) => t + o.lng, 0) / grupo.length;
    grupo.forEach((o, k) => { usados.add(o.id); desplazamiento.set(o.id, { k, n: grupo.length, lat, lng }); });
  }
}

function crearMarcadores() {
  agruparCercanas();
  for (const s of state.salas.filter(tieneUbicacion)) {
    const m = L.marker([s.lat, s.lng], { icon: iconoCasa(s), riseOnHover: true, keyboard: false });
    m.on("click", () => abrirSala(s));
    marcadores.set(s.id, m);
  }
}

function actualizarMarcadores() {
  const foto = mapa.getZoom() >= ZOOM_FOTOS;
  const cambioModo = foto !== modoFoto;
  modoFoto = foto;
  for (const [id, m] of marcadores) {
    const s = state.salaPorId.get(id);
    if (visible(s)) {
      if (cambioModo || !mapa.hasLayer(m)) {
        const d = desplazamiento.get(id);
        m.setLatLng(foto && d && d.n > 1 ? [d.lat, d.lng] : [s.lat, s.lng]);
        m.setIcon(foto ? iconoFoto(s) : iconoCasa(s));
      }
      if (!mapa.hasLayer(m)) m.addTo(mapa);
    } else if (mapa.hasLayer(m)) {
      m.remove();
    }
  }
  $("aviso-zoom").classList.toggle("oculto", foto || mapa.getZoom() < 13);
}

mapa.on("zoomend", actualizarMarcadores);

/* ================= Ubicación ================= */

let marcadorUsuario;
function fijarUbicacion(lat, lng, centrar) {
  state.user = { lat, lng };
  const icon = L.divIcon({ className: "", html: '<div class="punto-usuario"></div>', iconSize: [18, 18] });
  if (marcadorUsuario) marcadorUsuario.setLatLng([lat, lng]);
  else marcadorUsuario = L.marker([lat, lng], { icon, zIndexOffset: 1000, interactive: false }).addTo(mapa);
  if (centrar) mapa.setView([lat, lng], Math.max(mapa.getZoom(), 13));
  renderListas();
}

// Ubicación automática por GPS: se sigue en tiempo real (watch) y se centra el mapa
// solo la primera vez. El botón de la esquina vuelve a centrar en tu posición.
let seguimientoGps = null, primeraUbicacion = true;

function nativoGeo() {
  const Cap = window.Capacitor;
  return Cap?.isNativePlatform?.() ? (Cap.Plugins?.Geolocation || Cap.registerPlugin?.("Geolocation")) : null;
}

function alRecibirPosicion(pos) {
  if (!pos?.coords) return;
  fijarUbicacion(pos.coords.latitude, pos.coords.longitude, primeraUbicacion);
  primeraUbicacion = false;
  $("aviso-ubicacion").hidden = true;
}

function alFallarGps() {
  const aviso = $("aviso-ubicacion");
  aviso.hidden = false;
  aviso.textContent = "Activa la ubicación del celular y da permiso a ¿Qué dan? para ver los cines cercanos.";
}

async function iniciarUbicacion() {
  const opciones = { enableHighAccuracy: true, timeout: 15000, maximumAge: 30000 };
  const Geo = nativoGeo();
  try {
    if (Geo) {
      const permiso = await Geo.requestPermissions().catch(() => null);
      if (permiso && permiso.location === "denied") return alFallarGps();
      seguimientoGps = await Geo.watchPosition(opciones, (pos, err) => (err ? alFallarGps() : alRecibirPosicion(pos)));
    } else if (navigator.geolocation) {
      seguimientoGps = navigator.geolocation.watchPosition(alRecibirPosicion, alFallarGps, opciones);
    } else {
      alFallarGps();
    }
  } catch {
    alFallarGps();
  }
}

function centrarEnMiUbicacion() {
  if (state.user) mapa.setView([state.user.lat, state.user.lng], Math.max(mapa.getZoom(), 14));
  else { primeraUbicacion = true; iniciarUbicacion(); }
}

/* ================= Plantillas ================= */

function horarios(fs, max = 8) {
  if (!fs.length) return `<p class="nota">Sin funciones ${esHoy() ? "para hoy" : "para este día"}${state.idioma || state.formato ? " con estos filtros" : ""}</p>`;
  return `<div class="horarios">${fs.slice(0, max).map((f) => {
    const m = minutosHasta(f.hora);
    const pronto = m >= 0 && m <= 60;
    const extra = pronto ? `en ${Math.max(1, Math.round(m))} min` : [f.formato, f.idioma ? f.idioma.slice(0, 3).toUpperCase() : ""].filter(Boolean).join(" ");
    const contenido = `${fmtHora(f.hora)}${extra ? `<small>${esc(extra)}</small>` : ""}`;
    // Cada horario lleva a la página del cine para comprar esa función
    return f.url_compra
      ? `<a class="hora${pronto ? " pronto" : ""}" href="${esc(f.url_compra)}" target="_blank" rel="noopener" title="Comprar en la página del cine">${contenido}</a>`
      : `<span class="hora${pronto ? " pronto" : ""}">${contenido}</span>`;
  }).join("")}</div>`;
}

function meta(s) {
  const d = distanciaA(s);
  const quien = s.operador === TIPO[s.tipo] ? TIPO[s.tipo] : `${esc(s.operador)} · ${TIPO[s.tipo]}`;
  return `<div class="meta">${quien}${d != null ? ` · <strong>${fmtKm(d)}</strong>` : ""}
    ${s.zona ? `<br>${esc(s.zona)}` : ""}</div>${s.nota ? `<p class="nota">${esc(s.nota)}</p>` : ""}`;
}

function miniatura(s) {
  const bg = s.foto ? ` style="background-image:url('${esc(s.foto)}')"` : "";
  return `<div class="miniatura"${bg}>${s.foto ? "" : pinSala(s, 26)}</div>`;
}

function poster(p, clase = "cinta") {
  const url = state.posters[p];
  return url
    ? `<img class="${clase} con-poster" src="${esc(url)}" alt="" loading="lazy" onerror="this.replaceWith(Object.assign(document.createElement('div'),{className:'${clase}'}))">`
    : `<div class="${clase}"></div>`;
}

function agrupar(fs) {
  const m = new Map();
  for (const f of fs) (m.get(f.pelicula) || m.set(f.pelicula, []).get(f.pelicula)).push(f);
  return [...m];
}

/* ================= Vistas ================= */

function renderCerca() {
  const ul = $("lista-cerca");
  if (!state.user) {
    ul.innerHTML = '<li class="vacio"><b>¿Dónde estás?</b>Activa la ubicación del celular para ver los cines cercanos.</li>';
    return;
  }
  const items = [];
  for (const s of state.salas) {
    if (!visible(s) || !tieneUbicacion(s)) continue;
    const d = distanciaKm(state.user, s);
    if (d > state.radioKm) continue;
    let fs = (state.funcionesPorSala.get(s.id) || []).filter(vigente);
    if (state.soloProximaHora && esHoy()) { fs = fs.filter((f) => enProximaHora(f.hora)); if (!fs.length) continue; }
    items.push({ s, d, fs });
  }
  items.sort((a, b) => a.d - b.d);

  ul.innerHTML = items.length ? items.map(({ s, fs }) => `
    <li class="tarjeta" data-sala="${esc(s.id)}">
      <div class="tarjeta-franjas"></div>
      <div class="tarjeta-cuerpo">
        <div class="tarjeta-cabeza">${miniatura(s)}<div><h3>${esc(s.nombre)}</h3>${meta(s)}</div></div>
        ${agrupar(fs).slice(0, 3).map(([p, x]) => `<div class="peli"><h4>${esc(p)}</h4>${horarios(x, 6)}</div>`).join("") || horarios([])}
      </div>
    </li>`).join("")
    : `<li class="vacio"><b>Corte.</b>No hay salas ${state.soloProximaHora ? "con funciones en la próxima hora " : ""}a menos de ${state.radioKm} km.</li>`;
}

function renderPeliculas() {
  const q = state.busqueda;
  const filas = [];
  for (const [p, fs] of state.funcionesPorPeli) {
    if (q && !p.toLowerCase().includes(q)) continue;
    const vig = fs.filter((f) => vigente(f) && visible(state.salaPorId.get(f.sala_id)));
    if (!vig.length) continue;
    const sig = esHoy() ? vig.find((f) => minutosHasta(f.hora) >= 0) : vig[0];
    filas.push({ p, n: new Set(vig.map((f) => f.sala_id)).size, pronto: vig.filter((f) => enProximaHora(f.hora)).length, sig });
  }
  filas.sort((a, b) => b.pronto - a.pronto || a.p.localeCompare(b.p, "es"));
  $("lista-peliculas").innerHTML = filas.length ? filas.map(({ p, n, pronto, sig }) => `
    <li class="tarjeta" data-peli="${esc(p)}">
      <div class="fila-peli">${poster(p)}
        <div><h3>${esc(p)}</h3><div class="meta">${sig ? `${esHoy() ? "Próxima" : "Primera"}: ${fmtHora(sig.hora)}` : "Sin más funciones hoy"}${pronto ? ` · <strong>${pronto} en la próxima hora</strong>` : ""}</div></div>
        <span class="contador">${n}<small>sala${n > 1 ? "s" : ""}</small></span>
      </div>
    </li>`).join("")
    : q || state.idioma || state.formato
      ? '<li class="vacio"><b>Sin resultados</b>Prueba con otro título o quita los filtros.</li>'
      : esHoy()
        ? '<li class="vacio"><b>No quedan funciones hoy</b>Toca «Mañana» arriba para ver la próxima cartelera.</li>'
        : '<li class="vacio"><b>Sin funciones publicadas</b>Los cines aún no han subido la programación de este día.</li>';
}

function renderPizarra() {
  const ahora = new Date();
  $("campo-fecha").textContent = diaElegido().toLocaleDateString("es-CO", { weekday: "short", day: "numeric", month: "short" }).replace(".", "");
  $("campo-hora").textContent = fmtHora(ahora);
  $("campo-salas").textContent = state.salas.filter(visible).length;
}

// Días con funciones (desde hoy, máximo 7) y formatos presentes en la cartelera
function diasDisponibles() {
  const hoy = hoyCine().getTime(), dias = new Set([hoy]);
  for (const fs of state.funcionesPorSala.values())
    for (const f of fs) { const d = diaDeCine(f.hora).getTime(); if (d >= hoy) dias.add(d); }
  return [...dias].sort((a, b) => a - b).slice(0, 7).map((t) => new Date(t));
}
function formatosDisponibles() {
  const presentes = new Set();
  for (const fs of state.funcionesPorSala.values())
    for (const f of fs) { const F = (f.formato || "").toUpperCase(); FORMATOS.forEach((x) => F.includes(x) && presentes.add(x)); }
  return FORMATOS.filter((x) => presentes.has(x));
}
function renderBarraDia() {
  const hoy = hoyCine().getTime();
  const elegido = diaElegido().getTime();
  const dias = diasDisponibles().map((d) => {
    const t = d.getTime(), dif = Math.round((t - hoy) / 864e5);
    const arriba = dif === 0 ? "Hoy" : dif === 1 ? "Mañana" : d.toLocaleDateString("es-CO", { weekday: "short" }).replace(".", "");
    const abajo = d.toLocaleDateString("es-CO", { day: "numeric", month: "short" }).replace(".", "");
    return `<button class="dia${t === elegido ? " on" : ""}" data-dia="${t}"><b>${arriba}</b><small>${abajo}</small></button>`;
  }).join("");
  const op = (v, txt, sel) => `<option value="${v}"${v === sel ? " selected" : ""}>${txt}</option>`;
  const idiomas = op("", "Idioma: todos", state.idioma) + op("Doblada", "Doblada", state.idioma) +
    op("Subtitulada", "Subtitulada", state.idioma) + op("Original", "Original", state.idioma) + op("Español", "Español", state.idioma);
  const formatos = op("", "Formato: todos", state.formato) + formatosDisponibles().map((f) => op(f, f, state.formato)).join("");
  const html = `<div class="fila-dias">${dias}</div><div class="fila-filtros">` +
    `<select data-filtro="idioma" aria-label="Idioma">${idiomas}</select>` +
    `<select data-filtro="formato" aria-label="Formato">${formatos}</select></div>`;
  document.querySelectorAll("[data-barra]").forEach((b) => { b.innerHTML = html; });
  const interruptor = $("interruptor-hora");
  if (interruptor) interruptor.hidden = !esHoy();
}

function renderListas() {
  // Solo se dibuja la vista visible; las otras se dibujan al abrirlas
  if (state.vista !== "mapa") renderBarraDia();
  if (state.vista === "cerca") renderCerca();
  if (state.vista === "peliculas") renderPeliculas();
}

/* ================= Hoja de detalle ================= */

function abrirHoja(html) {
  $("hoja-cuerpo").innerHTML = html;
  $("hoja").hidden = false; $("velo").hidden = false;
  $("hoja").scrollTop = 0;
}
function cerrarHoja() { $("hoja").hidden = true; $("velo").hidden = true; }
$("hoja-cerrar").onclick = cerrarHoja;
$("velo").onclick = cerrarHoja;

function abrirSala(s) {
  const fs = (state.funcionesPorSala.get(s.id) || []).filter(vigente);
  const foto = s.foto ? `<div class="hoja-foto" style="background-image:url('${esc(s.foto)}')">
      ${s.foto_fuente ? `<span class="credito">Foto: <a href="${esc(s.foto_fuente)}" target="_blank" rel="noopener">Wikimedia Commons</a></span>` : ""}</div>` : "";
  const ir = tieneUbicacion(s)
    ? `<a class="boton-ir" href="https://www.google.com/maps/dir/?api=1&destination=${s.lat},${s.lng}" target="_blank" rel="noopener">➜ Cómo llegar</a>` : "";
  const compra = fs.find((f) => f.url_compra)?.url_compra;
  const comprar = compra ? `<a class="boton-ir boton-comprar" href="${esc(compra)}" target="_blank" rel="noopener">🎟 Ver en ${esc(s.operador)}</a>` : "";
  abrirHoja(`${foto}<div class="hoja-contenido"><h2>${esc(s.nombre)}</h2>${meta(s)}<div class="acciones">${ir}${comprar}</div><hr class="separador">
    ${agrupar(fs).map(([p, x]) => `<div class="peli peli-con-poster">${poster(p, "poster-mini")}<div><h4>${esc(p)}</h4>${horarios(x, 14)}</div></div>`).join("") || horarios([])}</div>`);
  if (tieneUbicacion(s)) mapa.panTo([s.lat, s.lng]);
}

function abrirPelicula(p) {
  const porSala = new Map();
  for (const f of state.funcionesPorPeli.get(p) || []) {
    const s = state.salaPorId.get(f.sala_id);
    if (!vigente(f) || !visible(s)) continue;
    (porSala.get(s) || porSala.set(s, []).get(s)).push(f);
  }
  const filas = [...porSala].sort((a, b) => (distanciaA(a[0]) ?? 1e9) - (distanciaA(b[0]) ?? 1e9));
  const muestra = (state.funcionesPorPeli.get(p) || [])[0] || {};
  const datos = [muestra.titulo_original && muestra.titulo_original !== p ? esc(muestra.titulo_original) : "",
    muestra.duracion_min ? `${muestra.duracion_min} min` : "", esc(muestra.clasificacion || "")].filter(Boolean).join(" · ");
  const cabeza = state.posters[p]
    ? `<div class="peli-cabeza">${poster(p, "poster-grande")}<div><h2>${esc(p)}</h2><div class="meta">${datos}</div></div></div>`
    : `<h2>${esc(p)}</h2><div class="meta">${datos}</div>`;
  const credito = state.posters[p] ? '<p class="credito-tmdb">Póster publicado por la sala de cine</p>' : "";
  abrirHoja(`<div class="hoja-contenido">${cabeza}<div class="meta">Salas ordenadas por cercanía</div>
    ${filas.map(([s, fs]) => `<div class="sala-en-peli" data-sala="${esc(s.id)}"><h4>${esc(s.nombre)}</h4>${meta(s)}${horarios(fs, 10)}</div>`).join("")}${credito}</div>`);
}

/* ================= Eventos (delegados) ================= */

$("lista-cerca").addEventListener("click", (e) => {
  if (e.target.closest("a")) return;   // un horario abre la página de compra, no la ficha
  const li = e.target.closest("[data-sala]"); if (li) abrirSala(state.salaPorId.get(li.dataset.sala));
});
$("lista-peliculas").addEventListener("click", (e) => {
  if (e.target.closest("a")) return;
  const li = e.target.closest("[data-peli]"); if (li) abrirPelicula(li.dataset.peli);
});
$("hoja-cuerpo").addEventListener("click", (e) => {
  if (e.target.closest("a")) return;
  const el = e.target.closest(".sala-en-peli[data-sala]"); if (el) abrirSala(state.salaPorId.get(el.dataset.sala));
});

document.querySelector(".pestanas").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-vista]"); if (!b) return;
  state.vista = b.dataset.vista;
  document.querySelectorAll(".pestanas button").forEach((x) => x.classList.toggle("activa", x === b));
  document.querySelectorAll(".vista").forEach((v) => v.classList.toggle("activa", v.id === `vista-${state.vista}`));
  cerrarHoja();
  if (state.vista === "mapa") requestAnimationFrame(() => mapa.invalidateSize());
  renderListas();
});

$("filtros").addEventListener("click", (e) => {
  const b = e.target.closest(".filtro"); if (!b) return;
  b.classList.toggle("on");
  b.classList.contains("on") ? state.tipos.add(b.dataset.tipo) : state.tipos.delete(b.dataset.tipo);
  actualizarMarcadores(); renderPizarra(); renderListas();
});

document.querySelectorAll("[data-barra]").forEach((barra) => {
  barra.addEventListener("click", (e) => {
    const b = e.target.closest(".dia"); if (!b) return;
    const t = +b.dataset.dia;
    state.dia = t === hoyCine().getTime() ? null : new Date(t);
    renderPizarra(); renderListas();
  });
  barra.addEventListener("change", (e) => {
    const s = e.target.closest("select[data-filtro]"); if (!s) return;
    state[s.dataset.filtro] = s.value;
    renderListas();
  });
});

$("radio").addEventListener("input", (e) => {
  state.radioKm = +e.target.value;
  $("radio-val").textContent = `${state.radioKm} km`;
  renderCerca();
});
$("proxima-hora").addEventListener("change", (e) => { state.soloProximaHora = e.target.checked; renderCerca(); });
$("buscar").addEventListener("input", debounce((e) => { state.busqueda = e.target.value.trim().toLowerCase(); renderPeliculas(); }, 150));
$("btn-ubicar").addEventListener("click", centrarEnMiUbicacion);
if (CFG_MAPA.PRIVACIDAD_URL) document.querySelectorAll("[data-privacidad]").forEach((a) => { a.href = CFG_MAPA.PRIVACIDAD_URL; });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") cerrarHoja(); });

/* ================= Inicio ================= */
(async () => {
  await cargarDatos();
  const sello = $("demo");
  sello.hidden = false;
  sello.textContent = state.demo ? "DEMO" : state.origen === "guardada" ? "SIN RED" : "AL DÍA";
  sello.title = state.generado ? `Cartelera del ${state.generado.toLocaleString("es-CO")}` : "";
  crearMarcadores();
  actualizarMarcadores();
  renderPizarra();
  iniciarUbicacion();
  // Cada minuto: reloj de la claqueta y etiquetas "en X min"
  setInterval(() => { renderPizarra(); renderListas(); }, 60000);
})();
