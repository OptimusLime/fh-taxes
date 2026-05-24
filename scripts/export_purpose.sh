#!/usr/bin/env bash
# Export the /purpose slide deck as a single self-contained HTML file.
#
# Reads from the Astro build output + esbuild bundle. No manual steps.
# Output: dist/fair-for-fair-haven.html (~68 KB, zero external deps except Google Fonts)
#
# Usage:
#   make export-purpose
#   # or directly:
#   bash scripts/export_purpose.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VIZ="$ROOT/viz"
DIST="$ROOT/dist"
ENTRY="$ROOT/temporary_scripts/purpose-entry.tsx"
ESBUILD="$ROOT/viz/node_modules/.bin/esbuild"
OUT="$DIST/fair-for-fair-haven.html"

# 1. Astro build (produces viz/dist/ with CSS + SSR HTML)
echo "[export-purpose] Building Astro site..."
cd "$VIZ" && npx astro build --silent 2>/dev/null || npx astro build

# 2. Find the purpose CSS (filename has a hash)
CSS_FILE=$(find "$VIZ/dist/_astro" -name 'purpose*.css' | head -1)
if [ -z "$CSS_FILE" ]; then
  echo "ERROR: Could not find purpose CSS in viz/dist/_astro/" >&2
  exit 1
fi
echo "[export-purpose] CSS: $CSS_FILE"

# 3. Bundle Deck + Preact + slides into one ESM JS file
echo "[export-purpose] Bundling JS with esbuild..."
mkdir -p "$DIST"
NODE_PATH="$VIZ/node_modules" "$ESBUILD" "$ENTRY" \
  --bundle --format=esm \
  --jsx=automatic --jsx-import-source=preact \
  --loader:.tsx=tsx \
  --outfile="$DIST/purpose-standalone.js"

# 4. Assemble single HTML
echo "[export-purpose] Assembling standalone HTML..."
python3 - "$CSS_FILE" "$DIST/purpose-standalone.js" "$OUT" << 'PYEOF'
import sys, os

css_path, js_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
css = open(css_path).read()
js = open(js_path).read()

html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fair for Fair Haven</title>
<style>
{css}
</style>
<style>
html, body {{ margin: 0; padding: 0; height: 100%; background: #FAFAF5; overflow: hidden; }}
body {{ font-family: 'Inter', -apple-system, system-ui, sans-serif; color: #0B0B0B; }}
.p-stage {{ height: 100vh !important; }}
</style>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body>
<div id="deck-root"></div>
<script type="module">
{js}
</script>
</body>
</html>'''

open(out_path, 'w').write(html)
print(f"[export-purpose] Written: {out_path} ({os.path.getsize(out_path) / 1024:.1f} KB)")
PYEOF

# 5. Cleanup intermediate
rm -f "$DIST/purpose-standalone.js"

echo "[export-purpose] Done. Open dist/fair-for-fair-haven.html in any browser."
