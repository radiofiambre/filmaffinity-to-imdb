# filmaffinity-to-imdb

Migra tus listas de [FilmAffinity](https://www.filmaffinity.com) a
[IMDb](https://www.imdb.com), sin tener que buscar y añadir cada título a
mano.

> ⚠️ Proyecto no oficial, para uso personal. Ni FilmAffinity ni IMDb ofrecen
> una API pública para esto, así que este proyecto depende de scraping
> (FilmAffinity) y de una API de terceros para el matching (OMDb). Si
> cualquiera de los dos sitios cambia su HTML/API, el proyecto puede dejar de
> funcionar hasta que se actualice.

## Qué hace

1. **Scrapea** una lista pública de FilmAffinity y extrae título, año y tipo
   (película/serie) de cada elemento.
2. **Resuelve** cada título a su ID de IMDb (`tt...`) usando la API gratuita
   de [OMDb](https://www.omdbapi.com/).
3. **Exporta** un CSV compatible con herramientas de importación de listas de
   IMDb (formato con columna `Const` = tt-ID), listo para subir con un
   userscript como [IMDb List Bulk
   Uploader](https://github.com/BonaFideBOSS/imdb-list-bulk-uploader).

```
FilmAffinity (lista) --scrape--> CSV intermedio --match (OMDb)--> CSV IMDb --import--> Lista en IMDb
```

## Instalación

```bash
git clone https://github.com/tu-usuario/filmaffinity-to-imdb.git
cd filmaffinity-to-imdb
pip install -e .
```

Necesitas una API key gratuita de OMDb: pídela en
https://www.omdbapi.com/apikey.aspx (tier gratuito: 1000 peticiones/día).
Guárdala en un fichero `.env` en la raíz del proyecto:

```
OMDB_API_KEY=tu_clave_aqui
```

## Uso

### 1. Encuentra la URL de tu lista

Entra en tu lista en FilmAffinity (debe ser pública), haz click en el icono de compartir y copia la URL completa. El enlace de compartir tiene esta forma:

\`\`\`
https://www.filmaffinity.com/es/userlist.php?user_id=TU_USER_ID&list_id=XXXXXX
\`\`\`

### 2. Pipeline completo (recomendado)

```bash
filmaffinity-to-imdb run "https://www.filmaffinity.com/es/userlist.php?user_id=TU_USER_ID&list_id=XXXXXX" \
    --list-name "Pendientes" \
    -o pendientes_imdb.csv
```

Esto genera:
- `pendientes_imdb.csv` — items resueltos con confianza alta, listos para
  importar.
- `pendientes_imdb_ambiguous.csv` — resueltos pero conviene revisarlos (p.ej.
  el año no coincidía exactamente).
- `pendientes_imdb_unmatched.csv` — no se encontraron en OMDb; tocará
  añadirlos a mano.

### 3. O paso a paso (útil para depurar)

```bash
filmaffinity-to-imdb scrape "https://www.filmaffinity.com/es/userlist.php?user_id=TU_USER_ID&list_id=XXXXXX" \
    --list-name "Pendientes" -o pendientes_fa.csv

filmaffinity-to-imdb match pendientes_fa.csv -o pendientes_imdb.csv
```

### 4. Importar en IMDb

1. Crea una lista vacía en IMDb.
2. Instala [Tampermonkey](https://www.tampermonkey.net/) (o similar) y el
   script [IMDb List Bulk
   Uploader](https://github.com/BonaFideBOSS/imdb-list-bulk-uploader).
3. Abre tu lista en IMDb y usa el script para pegar los IDs de
   `pendientes_imdb.csv` (columna `Const`).

## Limitaciones conocidas

- **Los selectores del scraper son un punto de partida**, no una garantía:
  se han definido según patrones documentados de FilmAffinity, pero conviene
  validarlos contra una lista real y ajustarlos en `scraper.py` (variable
  `SELECTORS`) si no extraen bien los datos.
- El matching por título+año puede fallar con remakes, títulos traducidos de
  forma distinta en España, o series con nombres de temporada distintos.
  Revisa siempre `_ambiguous.csv` y `_unmatched.csv`.
- No hay forma de escribir directamente en IMDb sin un userscript o
  automatización de navegador (IMDb no tiene API de escritura pública).
- Solo migra título/año/tipo — no reseñas ni valoraciones personales.

## Desarrollo

```bash
pip install -e ".[dev]"
pytest
```

Los tests del scraper usan un fixture HTML local (`tests/fixtures/`), no
hacen peticiones reales a FilmAffinity. Los tests del matcher mockean la API
de OMDb con la librería `responses`.

## Roadmap / ideas pendientes

- [ ] Automatizar la subida a IMDb con Playwright (en vez de depender de un
      userscript manual).
- [ ] Soporte para varias listas en una sola ejecución.
- [ ] Modo interactivo para resolver a mano los `_ambiguous` y `_unmatched`.

## Licencia

MIT
