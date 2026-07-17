#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PVE_HOST=${PVE_HOST:-pve}
HA_VMID=${HA_VMID:-100}

guest() {
	ssh "${PVE_HOST}" "qm guest exec ${HA_VMID} --timeout ${2:-300} -- /bin/sh -c $(printf '%q' "$1")" |
		python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("out-data") or d.get("err-data") or "")'
}

send() {
	local archive=$1 destination=$2
	scp -q "${archive}" "${PVE_HOST}:/tmp/dev.tgz"
	ssh "${PVE_HOST}" "B64=\$(base64 -w0 < /tmp/dev.tgz); qm guest exec ${HA_VMID} --timeout 120 -- /bin/sh -c \"echo \$B64 | base64 -d > /tmp/dev.tgz && tar xzf /tmp/dev.tgz -C ${destination} && chown -R root:root ${destination} && rm -f /tmp/dev.tgz\"" >/dev/null
}

rm -rf custom_components/outbound_webhooks/__pycache__
tar czf /tmp/integration.tgz custom_components
send /tmp/integration.tgz /mnt/data/supervisor/homeassistant

guest "docker exec hassio_cli ha core restart >/dev/null 2>&1; echo 'Home Assistant is restarting'"
