# filmaffinity-to-imdb

Migra tus listas de [FilmAffinity](https://www.filmaffinity.com) (películas
y series, con tu nota personal incluida) a [IMDb](https://www.imdb.com),
sin tener que buscar y añadir cada título a mano.

> ⚠️ Proyecto no oficial, para uso personal. Ni FilmAffinity ni IMDb ofrecen
> una API pública para esto: este proyecto depende de scraping
> (FilmAffinity) y de la API de [TMDb](https://www.themoviedb.org) para el
> matching de títulos. Si cualquiera de los dos sitios cambia su web, el
> proyecto puede dejar de funcionar hasta que se actualice.

## Qué hace

1. **Scrapea** una lista pública de FilmAffinity: título, año, tipo
   (película/serie) y tu nota personal de cada elemento si la tuviera.
2. **Resuelve** cada título a su ID de IMDb (`tt...`) usando la API de TMDb,
   que compara contra títulos traducidos (necesario porque FilmAffinity
   muestra los títulos en español, pero IMDb indexa por título original).
3. **Exporta** un CSV con el mismo formato que usa el propio IMDb, listo
   para importar.

Cada lista genera sus propios ficheros, nombrados a partir del nombre de la
lista, así que puedes migrar varias sin que se pisen entre sí:

```
lista_de_peliculas.csv             -> resueltos con confianza alta
lista_de_peliculas_ambiguous.csv   -> resueltos con duda, revísalo
lista_de_peliculas_unmatched.csv   -> no se encontraron en TMDb, añádelos a mano
```

## Instalación

```bash
git clone https://github.com/tu-usuario/filmaffinity-to-imdb.git
cd filmaffinity-to-imdb
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

Necesitas una API key gratuita de TMDb (v3 auth):
https://www.themoviedb.org/settings/api. Guárdala en un fichero `.env` en la
raíz del proyecto (copia `.env.example`):

```
TMDB_API_KEY=tu_clave_aqui
```

## Uso

### 1. Haz pública la lista en FilmAffinity

El scraper solo puede acceder a listas **públicas**. Dentro de FilmAffinity,
en la lista que quieras migrar, márcala como pública y usa su opción de
**compartir** para obtener el enlace. Debe tener esta forma:

```
https://www.filmaffinity.com/es/userlist.php?user_id=TU_USER_ID&list_id=XXXXXX
```

### 2. Genera el CSV para IMDb

```bash
filmaffinity-to-imdb run "https://www.filmaffinity.com/es/userlist.php?user_id=TU_USER_ID&list_id=XXXXXX" \
    --list-name "Lista de peliculas"
```

Al terminar verás un resumen como:

```
Resueltos: 516 | Ambiguos: 28 | Sin encontrar: 0 | Total: 544
CSV listo para importar en IMDb: lista_de_peliculas.csv
Revisar antes de importar: lista_de_peliculas_ambiguous.csv
```

Revisa `_ambiguous.csv` a mano antes del siguiente paso. En ocasiones, los datos de un título que hay en FilmAffinity no coinciden con los de TMDb, como podría ser el año. Esos títulos aparecerán en esta lista.

También puedes hacerlo en dos pasos si prefieres inspeccionar el CSV intermedio antes de gastar peticiones de TMDb:

```bash
filmaffinity-to-imdb scrape "https://www.filmaffinity.com/es/userlist.php?user_id=TU_USER_ID&list_id=XXXXXX" \
    --list-name "Lista de peliculas"

filmaffinity-to-imdb match lista_de_peliculas_fa.csv
```

### 3. Importa el CSV en IMDb

IMDb no tiene importación de listas por API, pero sí una herramienta oficial de importación por CSV en:

**https://www.imdb.com/es-es/labs/import-watch-history/**

Sube ahí `lista_de_peliculas.csv`.
Si tienes algún archivo `_ambiguous.csv`, revísa si está correcto antes de subirlo. Los títulos que no sean correctos deberás incluirlos a mano en tu lista de IMDB.
Los títulos en `_unmatched.csv` también los tendrás que añadir a mano.

El formato del CSV que genera este proyecto es compatible con esa herramienta porque replica las mismas columnas que usa el propio IMDb al exportar tus listas (`Const`, `Title`, `Year`, `Your Rating`, etc.).

Repite el proceso (pasos 1-3) para cada lista que quieras migrar.

## Limitaciones conocidas

- **Los selectores del scraper están validados contra el HTML real de FilmAffinity** (a fecha de creación de este proyecto), pero si FilmAffinity cambia su maquetación, tocará ajustar `SELECTORS` en `scraper.py`.
- El matching por título+año puede fallar con remakes o títulos con el mismo nombre. Revisa siempre `_ambiguous.csv` y `_unmatched.csv` antes de importar.
- Solo migra título, año, tipo y tu nota personal — no reseñas de texto.
- FilmAffinity está detrás de Cloudflare; el scraper usa `cloudscraper` para sortear el challenge anti-bot, pero si Cloudflare endurece la protección en el futuro, esto podría dejar de bastar.

## Desarrollo

```bash
pip install -e ".[dev]"
pytest
```

Los tests del scraper usan un fixture HTML local (`tests/fixtures/`), no hacen peticiones reales a FilmAffinity. Los tests del matcher y del exportador no hacen peticiones de red reales (mockeadas con `responses`, o sin red en absoluto).

## Licencia

@RadioFiambre
