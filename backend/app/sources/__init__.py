from app.sources.biblored import Biblored
from app.sources.cine_colombia import CineColombia
from app.sources.cinemark import Cinemark
from app.sources.cinemateca import Cinemateca
from app.sources.cinepolis import Cinepolis
from app.sources.manual import Manual
from app.sources.procinal import Procinal
from app.sources.royal_films import RoyalFilms

FUENTES = {f.nombre: f for f in [
    CineColombia(), Cinemark(), RoyalFilms(), Procinal(), Cinepolis(),
    Cinemateca(), Biblored(), Manual(),
]}
