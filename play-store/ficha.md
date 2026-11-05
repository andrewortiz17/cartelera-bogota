# BogoCine en Google Play: textos y respuestas

Todo lo que pide Play Console, listo para copiar. Las imágenes están en esta misma carpeta:
`icono-512.png`, `grafico-1024x500.png` y `capturas/` (se regeneran con `tomar-capturas.bat`).

## Ficha de la tienda

**Nombre de la app** (máx. 30): `BogoCine: cartelera de Bogotá`

**Descripción breve** (máx. 80):
`Todos los cines de Bogotá en un mapa: horarios, cineclubes y la sala más cerca.`

**Descripción completa** (máx. 4000):

```
BogoCine reúne en un solo lugar la cartelera de los cines de Bogotá: las grandes cadenas, la Cinemateca de Bogotá, las salas independientes y los cineclubes.

¿QUÉ PUEDES HACER?
• Ver en un mapa todos los cines de la ciudad y cuáles tienes más cerca.
• Buscar una película y ver en qué salas y a qué hora la dan, ordenadas por distancia.
• Mirar la programación de hoy y de los próximos días.
• Filtrar por idioma (doblada o subtitulada) y por formato (2D, 3D, IMAX, 4DX, VIP…).
• Ver solo las funciones que empiezan en la próxima hora.
• Tocar un horario para ir directo a la página de compra del cine.
• Consultar la última cartelera aunque no tengas internet.

CINES INCLUIDOS
Cinemark, Procinal, Royal Films, Cinépolis, Viziona, la Cinemateca de Bogotá y sus salas, Cinemanía, cineclubes como El Muro y más. Cine Colombia aparece en el mapa; sus horarios se sumarán cuando haya acuerdo de datos.

TU PRIVACIDAD
BogoCine no pide cuenta ni registro. Tu ubicación se usa dentro del celular para ordenar los cines por cercanía; tus coordenadas no se envían a ningún servidor.

BogoCine es un proyecto independiente hecho en Bogotá y no está afiliado a ninguna cadena de cine. Los horarios, precios y la venta de boletas son responsabilidad de cada sala; confirma siempre en su página antes de ir.
```

**Categoría:** Entretenimiento · **Etiquetas:** Películas, Cine, Bogotá
**Correo de contacto:** el tuyo (Play lo exige y queda público en la ficha)
**Política de privacidad:** `https://andrewortiz17.github.io/cartelera-bogota/privacidad.html`

## Seguridad de los datos (Data safety)

| Pregunta | Respuesta |
|---|---|
| ¿Tu app recopila o comparte alguno de los tipos de datos del usuario requeridos? | **Sí** (ubicación aproximada, ver abajo) |
| ¿Todos los datos están encriptados en tránsito? | **Sí** (todo va por HTTPS) |
| ¿Los usuarios pueden pedir que se borren sus datos? | **No se guardan datos fuera del dispositivo** — responde "No" y explica que borrar los datos de la app los elimina |
| Ubicación precisa | **No recopilada** — el GPS solo se usa dentro del celular (Google aclara que lo que se procesa en el dispositivo y no sale de él no se declara) |
| Ubicación aproximada | **Recopilada: Sí · Compartida: No · Procesada de forma efímera: Sí · Obligatoria: No · Fin: Funcionalidad de la app.** Es la opción prudente: al centrar el mapa en ti, la app pide a MapTiler/Esri las imágenes de esa zona, y eso revela la zona aproximada. Los proveedores que trabajan para la app no cuentan como "compartir". |
| Información personal, mensajes, fotos, contactos, historial, identificadores | **No** |
| Información de la app y rendimiento (fallos, diagnósticos) | **No** |

> Si más adelante agregas anuncios (AdMob), cambia esto: AdMob recopila el ID de publicidad,
> la ubicación aproximada por IP y datos de diagnóstico, y hay que declararlos y actualizar la política.

## Otras secciones de "Contenido de la app"

- **Acceso a la app:** toda la funcionalidad está disponible sin restricciones (no hay inicio de sesión).
- **Anuncios:** No, la app no contiene anuncios.
- **Clasificación de contenido:** categoría "Referencia, noticias o educación" o "Otra"; responde **No** a violencia, sexo, lenguaje, drogas, apuestas e interacción entre usuarios. Ojo: muestra pósteres de películas (algunas de terror), por eso en "contenido generado o de terceros" di que muestra pósteres e información de películas publicados por los cines.
- **Público objetivo:** 13+ (o 18+). Evita marcar menores de 13, porque eso activa las reglas de la política de Familias.
- **App de noticias:** No. **Apps gubernamentales:** No. **Funciones financieras:** No. **Salud:** No.
- **Permisos de ubicación:** solo en primer plano, así que no hace falta el formulario de ubicación en segundo plano.

## Pasos para publicar

1. Crea la cuenta de desarrollador en play.google.com/console (pago único de 25 USD).
   Las cuentas personales nuevas deben hacer una **prueba cerrada con al menos 12 personas durante 14 días** antes de poder publicar en producción.
2. Crea la app "BogoCine", idioma predeterminado Español (Latinoamérica), App, Gratis.
3. En GitHub: Actions → **Compilar para Google Play** → Run workflow → versión `1.0`. Descarga el artefacto y sube el `.aab`.
4. Llena la ficha con los textos y las imágenes de arriba, y las secciones de "Contenido de la app".
5. Prueba cerrada → invita a tus 12+ probadores → después de 14 días, solicita acceso a producción.
