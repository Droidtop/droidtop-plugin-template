#!/usr/bin/env bash
# Signs build.sh's output and packs <plugin id>.droidplugin.tar.xz.
#   PLUGIN_SIGNING_KEY_FILE=<key.pem> PLUGIN_SIGNING_CERT_FILE=<cert.pem> ./sign.sh
# manifest.jws is a detached ES256 JWS over the exact manifest.json bytes, with this repository's signing certificate in
# x5c (droidtop docs/plugin-api.md 1.5). droidtop follows that certificate to your root, which people trust once.
set -euo pipefail
cd "$(dirname "$0")"

: "${PLUGIN_SIGNING_KEY_FILE:?set to the path of the signing key of this repository, a PEM file}"
: "${PLUGIN_SIGNING_CERT_FILE:?set to the path of its certificate (PEM), issued by your root}"
for part in manifest.json plugin.py; do
  test -e "build/$part" || { echo "missing build/$part: run build.sh first" >&2; exit 1; }
done
PLUGIN_ID="$(python3 -c "import json; print(json.load(open('build/manifest.json'))['id'])")"

python3 -c 'import cryptography' 2>/dev/null || python3 -m pip install --quiet --user --break-system-packages 'cryptography>=42'
python3 tools/sign_jws.py droidtop-plugin+jws build/manifest.json "$PLUGIN_SIGNING_KEY_FILE" "$PLUGIN_SIGNING_CERT_FILE" > build/manifest.jws

OUT="${PLUGIN_ID}.droidplugin.tar.xz"
# The files are named in a fixed order, so GNU tar and macOS's bsdtar pack the same archive (no --sort, GNU only).
tar -C build -cf - manifest.json manifest.jws plugin.py | xz -9e > "$OUT"
echo "Signed $OUT"
python3 -c 'import hashlib, sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest(), sys.argv[1])' "$OUT"
