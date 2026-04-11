from typing import Any, Dict, Optional

from logger import get_logger

logger = get_logger("ai_audit")


def log_ai_generation_result(
    client: Any,
    topic: str,
    source_name: str,
    source_url: str,
    status: str,
    output_json: Optional[Dict[str, Any]] = None,
    failure_reason: Optional[str] = None,
) -> None:
    """Persist AI generation outcomes for observability."""
    try:
        selected_model = output_json.get("ai_model") if output_json else None
        payload = {
            "topic": topic[:500],
            "source_name": source_name[:120],
            "source_url": source_url[:1000],
            "status": status[:64],
            "selected_model": selected_model,
            "failure_reason": (failure_reason or "")[:1000] or None,
            "output_json": output_json,
            "validated": status == "generated",
        }
        client.from_("ai_generation_logs").insert(payload).execute()
    except Exception as e:
        # Keep ingestion resilient if audit logging fails.
        logger.warning(f"Failed to write AI audit log: {e}")
