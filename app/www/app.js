/* BogoCine — v0.2
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
  salas: [],
  salaPorId: new Map(),
  funcionesPorSala: new Map(),   // índice sala_id → funciones ordenadas
  funcionesPorPeli: new Map(),   // índice película → funciones
  user: null,
  tipos: new Set(Object.keys(TIPO)),
  radioKm: 5,
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
const vigente = (f) => minutosHasta(f.hora) >= -10;
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

  // Cartelera generada por los scrapers: primero la remota (si hay), luego la incluida en la app
  if (!funciones) {
    for (const url of [cfg.FUNCIONES_URL, "data/funciones.json"].filter(Boolean)) {
      try {
        const datos = await fetch(url, { cache: "no-store" }).then((r) => (r.ok ? r.json() : null));
        if (datos?.funciones?.length) {
          funciones = datos.funciones;
          state.generado = datos.generado ? new Date(datos.generado) : null;
          break;
        }
      } catch { /* sigue con la siguiente fuente */ }
    }
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
const capaBase = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
  maxZoom: 19, subdomains: "abcd",
  attribution: "© OpenStreetMap · © CARTO",
}).addTo(mapa);
let erroresMapa = 0, mapaCargo = false;
capaBase.on("tileload", () => { mapaCargo = true; $("aviso-mapa").hidden = true; });
capaBase.on("tileerror", () => {
  if (++erroresMapa > 6 && !mapaCargo) $("aviso-mapa").hidden = false;
});

const marcadores = new Map(); // sala_id → L.Marker (se crean una sola vez)
let modoFoto = null;

function iconoCasa(s) {
  return L.divIcon({ className: "marcador-pin", html: svgPin(GRIS[s.tipo]), iconSize: [30, 40], iconAnchor: [15, 39] });
}
function iconoFoto(s) {
  // Con foto: imagen de fondo. Sin foto: casa ilustrada en el tono de su tipo
  const bg = s.foto ? ` style="background-image:url('${esc(s.foto)}')"` : "";
  const img = `<div class="mf-img"${bg}>${s.foto ? "" : svgPin(GRIS[s.tipo], 30)}</div>`;
  return L.divIcon({
    className: "marcador-foto",
    html: `<div class="mf-franjas"></div>${img}<div class="mf-nombre"><i style="background:${GRIS[s.tipo]}"></i>${esc(s.nombre)}</div>`,
    iconSize: [132, 118], iconAnchor: [66, 118],
  });
}

function crearMarcadores() {
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
      if (cambioModo || !mapa.hasLayer(m)) m.setIcon(foto ? iconoFoto(s) : iconoCasa(s));
      if (!mapa.hasLayer(m)) m.addTo(mapa);
    } else if (mapa.hasLayer(m)) {
      m.remove();
    }
  }
  $("aviso-zoom").classList.toggle("oculto", foto || mapa.getZoom() < 13);
}

mapa.on("zoomend", actualizarMarcadores);
mapa.on("click", (e) => {
  fijarUbicacion(e.latlng.lat, e.latlng.lng, true);
  $("aviso-ubicacion").hidden = true;
});

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

async function obtenerUbicacion() {
  const aviso = $("aviso-ubicacion");
  try {
    const Cap = window.Capacitor;
    const Geo = Cap?.isNativePlatform?.() ? (Cap.Plugins?.Geolocation || Cap.registerPlugin?.("Geolocation")) : null;
    let pos;
    if (Geo) {
      await Geo.requestPermissions().catch(() => {});
      pos = await Geo.getCurrentPosition({ enableHighAccuracy: true, timeout: 10000 });
    } else {
      pos = await new Promise((ok, no) =>
        navigator.geolocation.getCurrentPosition(ok, no, { enableHighAccuracy: true, timeout: 10000 }));
    }
    fijarUbicacion(pos.coords.latitude, pos.coords.longitude, true);
    aviso.hidden = true;
  } catch {
    aviso.hidden = false;
    aviso.textContent = "No pude obtener tu ubicación (revisa el permiso y el GPS). Toca el mapa para fijarla.";
  }
}

/* ================= Plantillas ================= */

function horarios(fs, max = 8) {
  if (!fs.length) return '<p class="nota">Sin funciones cargadas para hoy</p>';
  return `<div class="horarios">${fs.slice(0, max).map((f) => {
    const m = minutosHasta(f.hora);
    const pronto = m >= 0 && m <= 60;
    const extra = pronto ? `en ${Math.max(1, Math.round(m))} min` : [f.formato, f.idioma ? f.idioma.slice(0, 3).toUpperCase() : ""].filter(Boolean).join(" ");
    return `<span class="hora${pronto ? " pronto" : ""}">${fmtHora(f.hora)}${extra ? `<small>${esc(extra)}</small>` : ""}</span>`;
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
  return `<div class="miniatura"${bg}>${s.foto ? "" : svgPin(GRIS[s.tipo], 24)}</div>`;
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
    ul.innerHTML = '<li class="vacio"><b>¿Dónde estás?</b>Activa la ubicación o toca el mapa.</li>';
    return;
  }
  const items = [];
  for (const s of state.salas) {
    if (!visible(s) || !tieneUbicacion(s)) continue;
    const d = distanciaKm(state.user, s);
    if (d > state.radioKm) continue;
    let fs = (state.funcionesPorSala.get(s.id) || []).filter(vigente);
    if (state.soloProximaHora) { fs = fs.filter((f) => enProximaHora(f.hora)); if (!fs.length) continue; }
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
    const sig = vig.find((f) => minutosHasta(f.hora) >= 0);
    filas.push({ p, n: new Set(vig.map((f) => f.sala_id)).size, pronto: vig.filter((f) => enProximaHora(f.hora)).length, sig });
  }
  filas.sort((a, b) => b.pronto - a.pronto || a.p.localeCompare(b.p, "es"));
  $("lista-peliculas").innerHTML = filas.length ? filas.map(({ p, n, pronto, sig }) => `
    <li class="tarjeta" data-peli="${esc(p)}">
      <div class="fila-peli"><div class="cinta"></div>
        <div><h3>${esc(p)}</h3><div class="meta">${sig ? `Próxima: ${fmtHora(sig.hora)}` : "Sin más funciones hoy"}${pronto ? ` · <strong>${pronto} en la próxima hora</strong>` : ""}</div></div>
        <span class="contador">${n}<small>sala${n > 1 ? "s" : ""}</small></span>
      </div>
    </li>`).join("")
    : '<li class="vacio"><b>Sin resultados</b>Prueba con otro título.</li>';
}

function renderPizarra() {
  const ahora = new Date();
  $("campo-fecha").textContent = ahora.toLocaleDateString("es-CO", { weekday: "short", day: "numeric", month: "short" }).replace(".", "");
  $("campo-hora").textContent = fmtHora(ahora);
  $("campo-salas").textContent = state.salas.filter(visible).length;
}

function renderListas() {
  // Solo se dibuja la vista visible; las otras se dibujan al abrirlas
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
    ${agrupar(fs).map(([p, x]) => `<div class="peli"><h4>${esc(p)}</h4>${horarios(x, 14)}</div>`).join("") || horarios([])}</div>`);
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
  abrirHoja(`<div class="hoja-contenido"><h2>${esc(p)}</h2><div class="meta">${datos ? datos + "<br>" : ""}Salas ordenadas por cercanía</div>
    ${filas.map(([s, fs]) => `<div class="sala-en-peli" data-sala="${esc(s.id)}"><h4>${esc(s.nombre)}</h4>${meta(s)}${horarios(fs, 10)}</div>`).join("")}</div>`);
}

/* ================= Eventos (delegados) ================= */

$("lista-cerca").addEventListener("click", (e) => {
  const li = e.target.closest("[data-sala]"); if (li) abrirSala(state.salaPorId.get(li.dataset.sala));
});
$("lista-peliculas").addEventListener("click", (e) => {
  const li = e.target.closest("[data-peli]"); if (li) abrirPelicula(li.dataset.peli);
});
$("hoja-cuerpo").addEventListener("click", (e) => {
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

$("radio").addEventListener("input", (e) => {
  state.radioKm = +e.target.value;
  $("radio-val").textContent = `${state.radioKm} km`;
  renderCerca();
});
$("proxima-hora").addEventListener("change", (e) => { state.soloProximaHora = e.target.checked; renderCerca(); });
$("buscar").addEventListener("input", debounce((e) => { state.busqueda = e.target.value.trim().toLowerCase(); renderPeliculas(); }, 150));
$("btn-ubicar").addEventListener("click", obtenerUbicacion);
document.addEventListener("keydown", (e) => { if (e.key === "Escape") cerrarHoja(); });

/* ================= Inicio ================= */
(async () => {
  await cargarDatos();
  const sello = $("demo");
  sello.hidden = false;
  sello.textContent = state.demo ? "DEMO" : "AL DÍA";
  sello.title = state.generado ? `Actualizado ${state.generado.toLocaleString("es-CO")}` : "";
  crearMarcadores();
  actualizarMarcadores();
  renderPizarra();
  obtenerUbicacion();
  // Cada minuto: reloj de la claqueta y etiquetas "en X min"
  setInterval(() => { renderPizarra(); renderListas(); }, 60000);
})();
