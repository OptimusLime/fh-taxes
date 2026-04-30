# Leaflet marker icons (vendored)

These three PNGs are vendored copies of the default Leaflet 1.9.4 marker
sprites. Source: `node_modules/leaflet/dist/images/`.

Vendored under `viz/public/` so they ship at known absolute paths
(`/leaflet/marker-icon.png`, etc.) — Astro's static-build pipeline does not
preserve the default Leaflet image-import resolution, which breaks the
`L.Icon.Default` paths on the deployed site.

`ParcelMap.astro` calls `L.Icon.Default.mergeOptions({ ... })` at runtime
to point at these absolute URLs.
