#!/usr/bin/env bash
# Builds the plugin bundle's contents, unsigned, into build/: plugin.py (src/plugin.py as it is) and manifest.json
# (manifest.template.json with the payload's SHA-256 and, in CI, the run number added to the version). Never touches a
# key: sign.sh signs and packs.
set -euo pipefail
cd "$(dirname "$0")"

rm -f -- build/manifest.json build/plugin.py
mkdir -p build
cp src/plugin.py build/plugin.py
python3 - <<'PY'
import hashlib, json, os

manifest = json.load(open("manifest.template.json"))
# Every file the plugin ships is listed with its hash; droidtop checks each one at install.
manifest["payload"] = [{"path": "plugin.py", "sha256": hashlib.sha256(open("build/plugin.py", "rb").read()).hexdigest()}]
# A CI build is published as <declared version>-<run number>, so every build has its own version.
build = os.environ.get("DROIDTOP_PLUGIN_BUILD", "").strip()
if build:
    if not build.isdigit():
        raise SystemExit("DROIDTOP_PLUGIN_BUILD must be a CI run number, got %r" % build)
    manifest["version"] = "%s-%s" % (manifest["version"], build)
json.dump(manifest, open("build/manifest.json", "w"), indent=2, sort_keys=True)
print("payload plugin.py, id=%s, version=%s" % (manifest["id"], manifest["version"]))
PY
python3 -c "import ast; ast.parse(open('build/plugin.py', encoding='utf-8').read())"
echo "Built build/plugin.py and build/manifest.json (unsigned)"
