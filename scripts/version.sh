#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

VERSION=${1:-}

if [[ ! "${VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
	echo "usage: scripts/version.sh <major.minor.patch>" >&2
	exit 64
fi

if [ -n "$(git status --porcelain)" ]; then
	echo "There are uncommitted changes. Commit them first." >&2
	exit 1
fi

python3 - "${VERSION}" <<'PY'
import json
import sys

path = "custom_components/outbound_webhooks/manifest.json"
manifest = json.load(open(path))
manifest["version"] = sys.argv[1]

with open(path, "w") as file:
    json.dump(manifest, file, indent=2)
    file.write("\n")
PY

git add custom_components/outbound_webhooks/manifest.json
git commit -m "chore: version ${VERSION}"
git tag -a "v${VERSION}" -m "Outbound Webhooks ${VERSION}"

echo
echo "Tagged v${VERSION}. Push it to release:"
echo
echo "  git push origin main && git push origin v${VERSION}"
