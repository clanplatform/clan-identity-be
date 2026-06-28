"""
HTTP client for the audit-service.

Call fire_audit_log() after any auth event (LOGIN, LOGOUT, PASSWORD_CHANGE, etc.).
Failures are always swallowed — a logging error must never fail the auth response.
"""
import httpx
from typing import Optional, Dict, Any
from core.config import settings


RISK_SCORE = {
    "LOGIN": "LOW",
    "LOGIN_FAILED": "MEDIUM",
    "LOGOUT": "LOW",
    "PASSWORD_CHANGE": "MEDIUM",
    "PASSWORD_RESET": "MEDIUM",
}


def fire_audit_log(
    *,
    action: str,
    object_type: str,
    object_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
    entity_id: Optional[str] = None,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    session_id: Optional[str] = None,
    risk_score: Optional[str] = None,
) -> None:
    """
    POST a single audit log entry to the audit-service.

    Standard action values:
        LOGIN | LOGIN_FAILED | LOGOUT | PASSWORD_CHANGE | PASSWORD_RESET
    """
    try:
        httpx.post(
            f"{settings.AUDIT_SERVICE_URL}/api/v1/logs",
            json={
                "action": action,
                "object_type": object_type,
                "object_id": object_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "entity_id": entity_id,
                "old_values": old_values or {},
                "new_values": new_values or {},
                "ip_address": ip_address,
                "user_agent": user_agent,
                "session_id": session_id,
                "risk_score": risk_score or RISK_SCORE.get(action, "LOW"),
            },
            timeout=2.0,
        )
    except Exception as exc:
        print(f"[audit-client] fire_audit_log failed: {exc}")
