"""
Login enrichment — derives device / network / risk details for login_attempts.

Everything here is computed SERVER-SIDE from the request transport (IP address
and User-Agent header). Nothing is trusted from the client body.

- Device fields: parsed from the User-Agent string. Uses the `user_agents`
  package when installed; otherwise falls back to a built-in regex parser
  (no extra dependency required).
- Network fields: ip_type via stdlib; country/region/city/ISP via MaxMind
  GeoLite2 when `geoip2` is installed and GEOIP_CITY_DB / GEOIP_ASN_DB env
  vars point to the .mmdb files. Otherwise left NULL.
- is_vpn / is_proxy / is_tor: default False — set by an IP-intelligence
  provider (e.g. IPQualityScore, ipinfo privacy API) when integrated in
  `detect_anonymizers()`.
- risk_score / is_suspicious: simple additive rule-based score (0-100).
"""
import ipaddress
import logging
import os
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# User-Agent parsing
# ---------------------------------------------------------------------------

_BROWSERS = [
    # order matters — Edge/Opera UAs also contain "Chrome", Chrome contains "Safari"
    ("Edge",    re.compile(r"Edg(?:e|A|iOS)?/([\d.]+)")),
    ("Opera",   re.compile(r"(?:OPR|Opera)/([\d.]+)")),
    ("Samsung Internet", re.compile(r"SamsungBrowser/([\d.]+)")),
    ("Firefox", re.compile(r"Firefox/([\d.]+)")),
    ("Chrome",  re.compile(r"(?:Chrome|CriOS)/([\d.]+)")),
    ("Safari",  re.compile(r"Version/([\d.]+).*Safari")),
]

_BOT_RE = re.compile(r"bot|crawler|spider|curl|wget|python-requests|httpx|postman", re.I)


def _short_version(version: str, parts: int = 2) -> str:
    return ".".join(version.split(".")[:parts])


def parse_user_agent(ua: Optional[str]) -> Dict[str, Optional[str]]:
    """Parse a User-Agent header into device/browser/os fields."""
    result: Dict[str, Optional[str]] = {
        "device_type": None,
        "device_name": None,
        "browser": None,
        "browser_version": None,
        "os": None,
        "os_version": None,
    }
    if not ua:
        return result

    # Preferred: user_agents package (if installed)
    try:
        from user_agents import parse as _ua_parse  # type: ignore

        parsed = _ua_parse(ua)
        result["browser"] = parsed.browser.family or None
        result["browser_version"] = parsed.browser.version_string or None
        result["os"] = parsed.os.family or None
        result["os_version"] = parsed.os.version_string or None
        result["device_name"] = (
            parsed.device.family if parsed.device.family != "Other" else None
        )
        if parsed.is_bot:
            result["device_type"] = "bot"
        elif parsed.is_tablet:
            result["device_type"] = "tablet"
        elif parsed.is_mobile:
            result["device_type"] = "mobile"
        else:
            result["device_type"] = "desktop"
        return result
    except ImportError:
        pass
    except Exception as exc:  # pragma: no cover — never block login on parsing
        logger.warning("UA parse via user_agents failed: %s", exc)

    # Fallback: built-in regex parser
    if _BOT_RE.search(ua):
        result["device_type"] = "bot"
    elif "iPad" in ua or "Tablet" in ua:
        result["device_type"] = "tablet"
    elif "Mobi" in ua or "iPhone" in ua or "Android" in ua:
        result["device_type"] = "mobile"
    else:
        result["device_type"] = "desktop"

    # OS
    m = re.search(r"Windows NT ([\d.]+)", ua)
    if m:
        nt_map = {"10.0": "10/11", "6.3": "8.1", "6.2": "8", "6.1": "7"}
        result["os"] = "Windows"
        result["os_version"] = nt_map.get(m.group(1), m.group(1))
        result["device_name"] = "Windows PC"
    elif "iPhone OS" in ua or "CPU iPhone" in ua:
        m = re.search(r"iPhone OS ([\d_]+)", ua)
        result["os"] = "iOS"
        result["os_version"] = m.group(1).replace("_", ".") if m else None
        result["device_name"] = "iPhone"
    elif "iPad" in ua:
        m = re.search(r"CPU OS ([\d_]+)", ua)
        result["os"] = "iPadOS"
        result["os_version"] = m.group(1).replace("_", ".") if m else None
        result["device_name"] = "iPad"
    elif "Mac OS X" in ua:
        m = re.search(r"Mac OS X ([\d_.]+)", ua)
        result["os"] = "macOS"
        result["os_version"] = m.group(1).replace("_", ".") if m else None
        result["device_name"] = "Mac"
    elif "Android" in ua:
        m = re.search(r"Android ([\d.]+)", ua)
        result["os"] = "Android"
        result["os_version"] = m.group(1) if m else None
        dm = re.search(r";\s*([^;)]+?)\s+Build/", ua)
        result["device_name"] = dm.group(1).strip() if dm else "Android device"
    elif "CrOS" in ua:
        result["os"] = "ChromeOS"
        result["device_name"] = "Chromebook"
    elif "Linux" in ua:
        result["os"] = "Linux"
        result["device_name"] = "Linux PC"

    # Browser
    for name, pattern in _BROWSERS:
        m = pattern.search(ua)
        if m:
            result["browser"] = name
            result["browser_version"] = _short_version(m.group(1))
            break

    return result


# ---------------------------------------------------------------------------
# IP / network enrichment
# ---------------------------------------------------------------------------

def _ip_type(ip: Optional[str]) -> Optional[str]:
    if not ip:
        return None
    try:
        addr = ipaddress.ip_address(ip)
        return "ipv6" if addr.version == 6 else "ipv4"
    except ValueError:
        return None


def _is_private(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return True


def lookup_geo(ip: Optional[str]) -> Dict[str, Optional[str]]:
    """
    Resolve country/region/city/ISP from the IP using MaxMind GeoLite2 when
    available (geoip2 package + GEOIP_CITY_DB / GEOIP_ASN_DB env vars).
    Returns NULLs otherwise — never blocks login.
    """
    result: Dict[str, Optional[str]] = {
        "country": None, "region": None, "city": None, "isp": None,
    }
    if not ip or _is_private(ip):
        return result

    try:
        import geoip2.database  # type: ignore
    except ImportError:
        return result

    city_db = os.getenv("GEOIP_CITY_DB")
    if city_db and os.path.exists(city_db):
        try:
            with geoip2.database.Reader(city_db) as reader:
                resp = reader.city(ip)
                result["country"] = resp.country.name
                result["region"] = (
                    resp.subdivisions.most_specific.name
                    if resp.subdivisions else None
                )
                result["city"] = resp.city.name
        except Exception as exc:
            logger.debug("GeoIP city lookup failed for %s: %s", ip, exc)

    asn_db = os.getenv("GEOIP_ASN_DB")
    if asn_db and os.path.exists(asn_db):
        try:
            with geoip2.database.Reader(asn_db) as reader:
                resp = reader.asn(ip)
                result["isp"] = resp.autonomous_system_organization
        except Exception as exc:
            logger.debug("GeoIP ASN lookup failed for %s: %s", ip, exc)

    return result


# Tor exit-node list — free, no API key (https://check.torproject.org).
# Cached in memory; refreshed at most every _TOR_TTL seconds; fail-open.
_TOR_EXIT_URL = "https://check.torproject.org/torbulkexitlist"
_TOR_TTL = 12 * 3600
_tor_exit_nodes: set = set()
_tor_fetched_at: float = 0.0


def _tor_exit_set() -> set:
    global _tor_exit_nodes, _tor_fetched_at
    import time
    import urllib.request

    now = time.monotonic()
    if _tor_fetched_at and now - _tor_fetched_at < _TOR_TTL:
        return _tor_exit_nodes
    try:
        req = urllib.request.Request(_TOR_EXIT_URL, headers={"User-Agent": "clan-auth-service"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
        _tor_exit_nodes = {line.strip() for line in body.splitlines() if line.strip()}
        _tor_fetched_at = now
        logger.info("Tor exit list refreshed: %d nodes", len(_tor_exit_nodes))
    except Exception as exc:
        # Fail-open: keep the stale set (possibly empty), retry after TTL
        _tor_fetched_at = now
        logger.debug("Tor exit list fetch failed: %s", exc)
    return _tor_exit_nodes


def detect_anonymizers(ip: Optional[str]) -> Dict[str, bool]:
    """
    VPN / proxy / Tor detection.
    - is_tor: checked against the free Tor exit-node list (cached 12h).
    - is_vpn / is_proxy: require a commercial IP-intelligence provider
      (IPQualityScore, ipinfo privacy API, ...) — integrate the call here.
      Default False so the columns are populated honestly.
    """
    result = {"is_vpn": False, "is_proxy": False, "is_tor": False}
    if not ip or _is_private(ip):
        return result
    result["is_tor"] = ip in _tor_exit_set()
    return result


# ---------------------------------------------------------------------------
# Risk scoring
# ---------------------------------------------------------------------------

def compute_risk(
    is_successful: bool,
    device: Dict[str, Any],
    anonymizers: Dict[str, bool],
    user_agent: Optional[str],
) -> Dict[str, Any]:
    """Simple additive rule-based risk score (0-100)."""
    score = 0
    reasons = []

    if not is_successful:
        score += 20
        reasons.append("failed_attempt")
    if anonymizers.get("is_tor"):
        score += 50
        reasons.append("tor")
    if anonymizers.get("is_vpn"):
        score += 25
        reasons.append("vpn")
    if anonymizers.get("is_proxy"):
        score += 25
        reasons.append("proxy")
    if device.get("device_type") == "bot":
        score += 40
        reasons.append("bot_user_agent")
    if not user_agent:
        score += 15
        reasons.append("missing_user_agent")

    score = min(score, 100)
    return {
        "risk_score": score,
        "is_suspicious": score >= 50,
        "suspicious_reason": ",".join(reasons) if score >= 50 else None,
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def enrich_login_attempt(
    ip_address: Optional[str],
    user_agent: Optional[str],
    is_successful: bool,
) -> Dict[str, Any]:
    """
    Build the full enrichment dict for a login_attempts row.
    Never raises — enrichment must not block login.
    """
    try:
        device = parse_user_agent(user_agent)
        geo = lookup_geo(ip_address)
        anonymizers = detect_anonymizers(ip_address)
        risk = compute_risk(is_successful, device, anonymizers, user_agent)
        return {
            "ip_type": _ip_type(ip_address),
            **geo,
            **anonymizers,
            **device,
            **risk,
        }
    except Exception as exc:  # pragma: no cover
        logger.warning("Login enrichment failed: %s", exc)
        return {}
