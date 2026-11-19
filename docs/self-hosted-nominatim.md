# Self-hosted Nominatim (Hungary) for the address pipeline

The public server (`nominatim.openstreetmap.org`) allows **one request per second** in total and forbids heavy use.
With it the pipeline still works, one request at a time (about 12 minutes for 700 addresses). A private Nominatim lifts
the limit so `GEOCODE_CONCURRENCY` (default 5) requests really run in parallel.

## Run it

```
docker run -d --name nominatim -p 8080:8080 \
  -e PBF_URL=https://download.geofabrik.de/europe/hungary-latest.osm.pbf \
  -e REPLICATION_URL=https://download.geofabrik.de/europe/hungary-updates/ \
  -v nominatim-data:/var/lib/postgresql/16/main \
  mediagis/nominatim:4.4
```

First start imports the extract (about 300 MB download, roughly 15-30 minutes, 2 GB RAM minimum, 4 GB comfortable).
Check: `curl "http://localhost:8080/search?q=1075+Budapest+Kazinczy+utca+14&format=jsonv2&limit=1"`.

## Point the app at it

| Setting | Value |
|---------|-------|
| `NOMINATIM_URL` | `http://<host>:8080/search` |
| `GEOCODE_CONCURRENCY` | `5` (raise carefully, the import host is the limit) |
| `NOMINATIM_MIN_INTERVAL` | leave empty: 1.0 s for the public host, 0 for any other host |

Render's free/starter instances are too small to host it; use a separate VM and keep it private (firewall to the app).

## Optional: street list for spelling correction

The parser ships a small Budapest street seed. To correct misspelled streets everywhere:

1. Export `zip<TAB>street` (or `settlement<TAB>street`) lines from the OSM Hungary extract (Overpass or `osmium`).
2. `python manage.py build_street_index streets.tsv streets_hu_osm.json`
3. Set `ADDRESS_STREETS_FILE=/path/streets_hu_osm.json`. The data is OpenStreetMap (ODbL): keep the attribution.

## Google (last resort)

Set `GOOGLE_GEOCODING_API_KEY` to enable stage 4. Only house-level, non-partial matches are accepted, restricted to
Hungary and the parsed postal code. Check Google's terms for storing results and for using them on a non-Google map
before enabling (open decision D2 in `docs/backlog/address-pipeline.md`).

## Measuring

`python manage.py smoke_real_services` prints the per-stage resolve rate for messy real addresses
(`pipeline resolve rate: 5/5 without a human; by stage {...}`).
