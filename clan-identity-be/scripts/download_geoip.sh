#!/usr/bin/env bash
# ============================================================================
# Download MaxMind GeoLite2 City + ASN databases into ./data/geoip/
# Used by auth-service login enrichment (GEOIP_CITY_DB / GEOIP_ASN_DB).
#
# Requires a FREE MaxMind account: https://www.maxmind.com/en/geolite2/signup
# Then create a license key and run:
#
#   MAXMIND_LICENSE_KEY=your_key ./scripts/download_geoip.sh
#
# GeoLite2 is updated twice weekly — re-run periodically (or via cron).
# ============================================================================
set -euo pipefail

if [ -z "${MAXMIND_LICENSE_KEY:-}" ]; then
    echo "ERROR: MAXMIND_LICENSE_KEY is not set."
    echo "Sign up (free): https://www.maxmind.com/en/geolite2/signup"
    exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$REPO_ROOT/data/geoip"
mkdir -p "$DEST"

download_edition() {
    local edition="$1"
    local url="https://download.maxmind.com/app/geoip_download?edition_id=${edition}&license_key=${MAXMIND_LICENSE_KEY}&suffix=tar.gz"
    local tmp
    tmp="$(mktemp -d)"

    echo "Downloading ${edition}..."
    curl -fsSL "$url" -o "$tmp/${edition}.tar.gz"
    tar -xzf "$tmp/${edition}.tar.gz" -C "$tmp"

    # Archive contains a dated folder, e.g. GeoLite2-City_20260707/GeoLite2-City.mmdb
    find "$tmp" -name "${edition}.mmdb" -exec mv {} "$DEST/${edition}.mmdb" \;
    rm -rf "$tmp"

    echo "  → $DEST/${edition}.mmdb"
}

download_edition "GeoLite2-City"
download_edition "GeoLite2-ASN"

echo ""
echo "Done. Restart auth-service to pick the files up:"
echo "  docker compose restart auth-service"
