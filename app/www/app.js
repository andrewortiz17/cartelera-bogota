/* Cartelera Bogotá — borrador v0.1
   - Mapa con todas las salas (Leaflet + OpenStreetMap)
   - "Cerca de mí": salas ordenadas por distancia, con filtro de próxima hora
   - Películas: dónde y a qué hora, ordenado por cercanía
   Si no hay backend configurado, usa datos de demostración. */

const BOGOTA = { lat: 4.6533, lng: -74.0836 };
const COLORES = {
  cadena: "#e8b04a", cinemateca: "#d9614c",
  independiente: "#6fb3a8", cineclub: "#a98bd8"
};
const TIPO_LABEL = {
  cadena: "Cadena", cinemateca: "Cinemateca",
  independiente: "Independiente", cineclub: "Cineclub"
};

const state = {
  salas: [],
  funciones: [],
  user: null,            // {lat, lng, aproximada}
  tipos: new Set(["cadena", "cinemateca", "independiente", "cineclub"]),
  radioKm: 5,
  soloProximaHora: false,
  demo: false,
};

/* ---------- Utilidades ---------- */

// Distancia en línea recta (fórmula de Haversine), en km
function distanciaKm(a, b) {
  const R = 6371, rad = (x) => (x * Math.PI) / 180;
  const dLat = rad(b.lat - a.lat), dLng = rad(b.lng - a.lng);
  const h = Math.sin(dLat / 2) ** 2 +
    Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}
const fmtKm = (km) => (km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(1)} km`);
const fmtHora = (d) => d.toLocaleTimeString("es-CO", { hour: "numeric", minute: "2-digit" });
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const tieneUbicacion = (s) => typeof s.lat === "number" && typeof s.lng === "number";
const enProximaHora = (d) => { const m = (d - Date.now()) / 60000; return m >= 0 && m <= 60; };

function salasVisibles() {
  return state.salas.filter((s) => state.tipos.has(s.tipo));
}
function funcionesDeSala(id) {
  const ahora = Date.now() - 10 * 60000; // muestra también las que empezaron hace <10 min
  return state.funciones
    .filter((f) => f.sala_id === id && f.hora.getTime() >= ahora)
    .sort((a, b) => a.hora - b.hora);
}
function distanciaA(sala) {
  if (!state.user || !tieneUbicacion(sala)) return null;
  return distanciaKm(state.user, sala);
}

/* ---------- Datos ---------- */

async function cargarDatos() {
  const api = (window.CARTELERA_CONFIG || {}).API_URL;
  if (api) {
    try {
      const [salas, funciones] = await Promise.all([
        fetch(`${api}/salas`).then((r) => r.json()),
        fetch(`${api}/funciones`).then((r) => r.json()),
      ]);
      state.salas = salas;
      state.funciones = funciones.map((f) => ({ ...f, hora: new Date(f.hora) }));
      return;
    } catch (e) {
      console.warn("Backend no disponible, usando demo:", e);
    }
  }
  const local = await fetch("data/salas.json").then((r) => r.json());
  state.salas = local.salas;
  state.funciones = generarFuncionesDemo(state.salas);
  state.demo = true;
}

// Horarios inventados para probar la interfaz (títulos ficticios)
function generarFuncionesDemo(salas) {
  const comerciales = ["El último tren a Zipaquirá", "Galaxia Rota", "Monstruos del Páramo",
    "Operación Andes", "La casa del río", "Pequeños héroes 3"];
  const arte = ["Niebla en La Candelaria", "Retrato de un silencio", "Ciclo: cine colombiano de los 80",
    "Documental: Memoria del agua", "Cortos universitarios", "Clásico restaurado: noche negra"];
  const formatos = ["2D", "3D", "IMAX", "XD"];
  const out = [];
  let seed = 7;
  const rnd = () => ((seed = (seed * 9301 + 49297) % 233280) / 233280);
  const hoy = new Date(); hoy.setSeconds(0, 0);

  for (const s of salas) {
    const esCadena = s.tipo === "cadena";
    const pelis = esCadena ? comerciales : arte;
    const n = esCadena ? 10 : 2 + Math.floor(rnd() * 2);
    for (let i = 0; i < n; i++) {
      const h = esCadena ? 11 + Math.floor(rnd() * 11) : 14 + Math.floor(rnd() * 6);
      const d = new Date(hoy); d.setHours(h, [0, 15, 30, 45][Math.floor(rnd() * 4)]);
      out.push({
        sala_id: s.id,
        pelicula: pelis[Math.floor(rnd() * pelis.length)],
        hora: d,
        formato: esCadena ? formatos[Math.floor(rnd() * formatos.length)] : "",
        idioma: rnd() > 0.5 ? "Doblada" : "Subtitulada",
      });
    }
  }
  return out;
}

/* ---------- Ubicación ---------- */

async function obtenerUbicacion() {
  const hint = document.getElementById("loc-hint");
  try {
    const Geo = window.Capacitor?.Plugins?.Geolocation;
    let pos;
    if (Geo) {
      await Geo.requestPermissions().catch(() => {});
      pos = await Geo.getCurrentPosition({ enableHighAccuracy: true, timeout: 10000 });
    } else {
      pos = await new Promise((ok, fail) =>
        navigator.geolocation.getCurrentPosition(ok, fail, { enableHighAccuracy: true, timeout: 10000 }));
    }
    fijarUbicacion(pos.coords.latitude, pos.coords.longitude, false);
    hint.hidden = true;
  } catch (e) {
    fijarUbicacion(BOGOTA.lat, BOGOTA.lng, true);
    hint.hidden = false;
    hint.textContent = "No pude obtener tu ubicación. Toca el mapa para fijarla.";
  }
}

let userMarker;
function fijarUbicacion(lat, lng, aproximada) {
  state.user = { lat, lng, aproximada };
  const icon = L.divIcon({ className: "", html: '<div class="user-dot"></div>', iconSize: [16, 16] });
  if (userMarker) userMarker.setLatLng([lat, lng]);
  else userMarker = L.marker([lat, lng], { icon, zIndexOffset: 1000 }).addTo(map);
  if (!aproximada) map.setView([lat, lng], 13);
  renderTodo();
}

/* ---------- Mapa ---------- */

const map = L.map("map", { zoomControl: false }).setView([BOGOTA.lat, BOGOTA.lng], 12);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "© OpenStreetMap",
}).addTo(map);
const capaSalas = L.layerGroup().addTo(map);

map.on("click", (e) => {
  fijarUbicacion(e.latlng.lat, e.latlng.lng, false);
  document.getElementById("loc-hint").hidden = true;
});

function renderMapa() {
  capaSalas.clearLayers();
  for (const s of salasVisibles().filter(tieneUbicacion)) {
    L.circleMarker([s.lat, s.lng], {
      radius: 9, color: "#14110f", weight: 2,
      fillColor: COLORES[s.tipo], fillOpacity: 0.95,
    })
      .on("click", (ev) => { L.DomEvent.stopPropagation(ev); abrirSala(s); })
      .addTo(capaSalas);
  }
}

/* ---------- Vistas ---------- */

function chipsHorario(funciones, max = 8) {
  if (!funciones.length) return '<p class="warn">Sin funciones cargadas para hoy</p>';
  return `<div class="times">${funciones.slice(0, max).map((f) =>
    `<span class="time ${enProximaHora(f.hora) ? "soon" : ""}">${fmtHora(f.hora)}${
      f.formato ? `<small>${esc(f.formato)}</small>` : ""}</span>`).join("")}</div>`;
}

function metaSala(s) {
  const d = distanciaA(s);
  return `<div class="meta"><span class="dot" style="background:${COLORES[s.tipo]}"></span>
    ${esc(s.operador)} · ${esc(TIPO_LABEL[s.tipo])}${d != null ? ` · <strong>${fmtKm(d)}</strong>` : ""}
    ${s.zona ? ` · ${esc(s.zona)}` : ""}</div>${s.nota ? `<p class="warn">${esc(s.nota)}</p>` : ""}`;
}

function renderCerca() {
  const ul = document.getElementById("lista-cerca");
  if (!state.user) { ul.innerHTML = '<li class="empty">Necesito tu ubicación.</li>'; return; }

  const items = salasVisibles()
    .filter(tieneUbicacion)
    .map((s) => ({ s, d: distanciaA(s), f: funcionesDeSala(s.id) }))
    .filter((x) => x.d <= state.radioKm)
    .map((x) => state.soloProximaHora ? { ...x, f: x.f.filter((f) => enProximaHora(f.hora)) } : x)
    .filter((x) => !state.soloProximaHora || x.f.length)
    .sort((a, b) => a.d - b.d);

  if (!items.length) {
    ul.innerHTML = `<li class="empty">No hay salas ${state.soloProximaHora ? "con funciones en la próxima hora " : ""}
      a menos de ${state.radioKm} km. Prueba ampliar el radio.</li>`;
    return;
  }
  ul.innerHTML = items.map(({ s, f }) => {
    const porPeli = agruparPorPelicula(f);
    return `<li class="card" data-sala="${esc(s.id)}"><h3>${esc(s.nombre)}</h3>${metaSala(s)}
      ${porPeli.slice(0, 3).map(([p, fs]) => `<h4 style="margin:10px 0 0;font-size:.88rem">${esc(p)}</h4>${chipsHorario(fs, 6)}`).join("")
      || chipsHorario([])}</li>`;
  }).join("");
  ul.querySelectorAll("[data-sala]").forEach((li) =>
    li.addEventListener("click", () => abrirSala(state.salas.find((s) => s.id === li.dataset.sala))));
}

function agruparPorPelicula(funciones) {
  const m = new Map();
  for (const f of funciones) {
    if (!m.has(f.pelicula)) m.set(f.pelicula, []);
    m.get(f.pelicula).push(f);
  }
  return [...m.entries()];
}

function renderPeliculas() {
  const q = document.getElementById("buscar").value.trim().toLowerCase();
  const visibles = new Set(salasVisibles().map((s) => s.id));
  const futuras = state.funciones.filter((f) => visibles.has(f.sala_id) && f.hora.getTime() >= Date.now() - 600000);
  const pelis = agruparPorPelicula(futuras)
    .filter(([p]) => !q || p.toLowerCase().includes(q))
    .sort((a, b) => a[0].localeCompare(b[0], "es"));

  const ul = document.getElementById("lista-peliculas");
  if (!pelis.length) { ul.innerHTML = '<li class="empty">No encontré películas.</li>'; return; }
  ul.innerHTML = pelis.map(([p, fs]) => {
    const nSalas = new Set(fs.map((f) => f.sala_id)).size;
    const prox = fs.filter((f) => enProximaHora(f.hora)).length;
    return `<li class="card" data-peli="${esc(p)}"><h3>${esc(p)}</h3>
      <div class="meta">${nSalas} sala${nSalas > 1 ? "s" : ""}${prox ? ` · <strong>${prox} en la próxima hora</strong>` : ""}</div></li>`;
  }).join("");
  ul.querySelectorAll("[data-peli]").forEach((li) =>
    li.addEventListener("click", () => abrirPelicula(li.dataset.peli)));
}

/* ---------- Hoja de detalle ---------- */

const sheet = document.getElementById("sheet");
const sheetBody = document.getElementById("sheet-body");
document.getElementById("sheet-close").onclick = () => (sheet.hidden = true);

function abrirSala(s) {
  const porPeli = agruparPorPelicula(funcionesDeSala(s.id));
  const nav = tieneUbicacion(s)
    ? `<p><a style="color:var(--accent)" href="https://www.openstreetmap.org/directions?to=${s.lat}%2C${s.lng}" target="_blank" rel="noopener">Cómo llegar ↗</a></p>` : "";
  sheetBody.innerHTML = `<h2>${esc(s.nombre)}</h2>${metaSala(s)}${nav}
    ${porPeli.length ? porPeli.map(([p, fs]) => `<h4>${esc(p)}</h4>${chipsHorario(fs, 12)}`).join("") : chipsHorario([])}`;
  sheet.hidden = false;
  if (tieneUbicacion(s)) map.panTo([s.lat, s.lng]);
}

function abrirPelicula(p) {
  const visibles = new Set(salasVisibles().map((s) => s.id));
  const porSala = new Map();
  for (const f of state.funciones) {
    if (f.pelicula !== p || !visibles.has(f.sala_id) || f.hora.getTime() < Date.now() - 600000) continue;
    if (!porSala.has(f.sala_id)) porSala.set(f.sala_id, []);
    porSala.get(f.sala_id).push(f);
  }
  const filas = [...porSala.entries()]
    .map(([id, fs]) => ({ s: state.salas.find((x) => x.id === id), fs: fs.sort((a, b) => a.hora - b.hora) }))
    .sort((a, b) => (distanciaA(a.s) ?? 1e9) - (distanciaA(b.s) ?? 1e9));
  sheetBody.innerHTML = `<h2>${esc(p)}</h2><div class="meta">Ordenado por cercanía</div>
    ${filas.map(({ s, fs }) => `<h4>${esc(s.nombre)}</h4>${metaSala(s)}${chipsHorario(fs, 10)}`).join("")}`;
  sheet.hidden = false;
}

/* ---------- Navegación y filtros ---------- */

document.querySelectorAll(".tabs button").forEach((b) => b.addEventListener("click", () => {
  document.querySelectorAll(".tabs button").forEach((x) => x.classList.toggle("active", x === b));
  document.querySelectorAll(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${b.dataset.view}`));
  sheet.hidden = true;
  if (b.dataset.view === "mapa") setTimeout(() => map.invalidateSize(), 50);
}));

document.querySelectorAll(".chip").forEach((c) => c.addEventListener("click", () => {
  c.classList.toggle("on");
  c.classList.contains("on") ? state.tipos.add(c.dataset.tipo) : state.tipos.delete(c.dataset.tipo);
  renderTodo();
}));

document.getElementById("radio").addEventListener("input", (e) => {
  state.radioKm = +e.target.value;
  document.getElementById("radio-val").textContent = `${state.radioKm} km`;
  renderCerca();
});
document.getElementById("proxima-hora").addEventListener("change", (e) => {
  state.soloProximaHora = e.target.checked; renderCerca();
});
document.getElementById("buscar").addEventListener("input", renderPeliculas);
document.getElementById("btn-locate").addEventListener("click", obtenerUbicacion);

function renderTodo() { renderMapa(); renderCerca(); renderPeliculas(); }

/* ---------- Inicio ---------- */
(async () => {
  await cargarDatos();
  document.getElementById("demo-banner").hidden = !state.demo;
  renderTodo();
  obtenerUbicacion();
  setInterval(renderTodo, 60000); // refresca "próxima hora" cada minuto
})();
