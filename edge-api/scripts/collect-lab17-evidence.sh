#!/usr/bin/env bash
# After `npx wrangler login` and `npx wrangler deploy`, capture text/JSON evidence for Lab 17 (no screenshots).
# Usage:
#   export WORKERS_DEV_URL="https://edge-api.<subdomain>.workers.dev"
#   ./scripts/collect-lab17-evidence.sh | tee lab17-evidence.txt
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -z "${WORKERS_DEV_URL:-}" ]]; then
  echo "error: set WORKERS_DEV_URL to your public workers.dev URL" >&2
  exit 1
fi

echo "# Lab 17 evidence (generated $(date -u +"%Y-%m-%dT%H:%M:%SZ") UTC)"
echo
echo "## wrangler whoami"
npx wrangler whoami
echo
echo "## wrangler deployments list"
npx wrangler deployments list
echo
echo "## HTTP responses (curl -sS)"
for path in / /health /edge /deploy /counter; do
  echo
  echo "### GET ${path}"
  if ! curl -sS -f "${WORKERS_DEV_URL%/}${path}"; then
    echo "(curl failed — run the same URL from your Mac terminal or browser; TLS/network in CI sandboxes often breaks here.)"
  fi
  echo
done
