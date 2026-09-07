# SatQuery AI

A judge-ready Earth observation dashboard inspired by the supplied UI reference, with real API integrations.

## What is live

- **Geocoding:** OpenStreetMap Nominatim (`/api/geocode`)
- **Satellite imagery:** Copernicus Data Space Sentinel Hub Process API + Sentinel-2 L2A (`/api/satellite`)
- **Weather/elevation:** Open-Meteo (`/api/weather`)
- **AI Query:** OpenAI Responses API (`/api/ai`) when `OPENAI_API_KEY` is configured
- **Maps:** Leaflet + OpenStreetMap tiles
- **UI:** React/Vite, responsive dark geospatial dashboard
- **Comparison:** requests two real satellite scenes for different date windows

## Run

```bash
npm install
cp server/.env.example server/.env
# add your Copernicus OAuth client id/secret
# optionally add OPENAI_API_KEY

npm run dev
```

Open `http://localhost:5173`.

## Copernicus credentials

Create an OAuth client in the Copernicus Data Space / Sentinel Hub account and put the client ID and secret in `server/.env`. The server requests OAuth tokens so the secret is never exposed in the browser.

The current Process API uses:
`https://sh.dataspace.copernicus.eu/process/v1`

and Sentinel-2 L2A:
`sentinel-2-l2a`.

## Production architecture

Browser -> Express API -> Copernicus / Nominatim / Open-Meteo / OpenAI.

For a production hackathon deployment:
1. Deploy the server as a Vercel/Node function or another backend.
2. Store secrets only as server environment variables.
3. Add a proper STAC/Catalog query for acquisition metadata.
4. Add NDVI/NDWI evalscripts and cache images by AOI/date.
5. Replace the demo report endpoint with a PDF worker.
6. Add PostGIS for saved projects and AOI polygons.

## API source notes

Copernicus documents the OAuth client-credentials flow and Process API. Nominatim provides free-form forward geocoding. Open-Meteo provides coordinate-based forecast/current data. OpenAI's Responses API supports text and image analysis.

## UPGRADED VERSION
- WebGL 3D globe with live location marker and animated arcs.
- Sentinel-2 true color, NDVI, NDWI and built-up spectral layers.
- Copernicus Catalog/STAC acquisition history with cloud metadata.
- Multimodal AI endpoint can inspect the current satellite image plus the user's question.
- Cleaner judge-demo flow: Search -> Earth view -> Layers -> Compare -> AI explanation -> acquisition evidence.

Official Copernicus references:
- https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html
- https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Process.html
- https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Catalog.html
