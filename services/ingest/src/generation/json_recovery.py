"""Recover valid JSON from malformed model output."""

import json
import re
from typing import Any, Dict, Optional


def recover_json(text: str) -> Optional[Dict[str, Any]]:
    """Attempt to recover valid JSON from malformed AI response."""
    text = text.strip()

    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'^```\w*\s*', '', text)
    text = re.sub(r'^```\s*', '', text)
    text = re.sub(r'```$', '', text)
    text = text.replace("```", "")

    text = re.sub(r'^Here is the JSON:.*?^\{', '{', text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r'^Here is the.*?:.*?^\{', '{', text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r'^\{.*', lambda m: m.group(0), text, flags=re.MULTILINE)

    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    text = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', text)

    text = re.sub(r',\s*\]', ']', text)
    text = re.sub(r',\s*\}', '}', text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    try:
        text = "{" + text.split("{", 1)[1]
        text = text.rsplit("}", 1)[0] + "}"
        return json.loads(text)
    except (json.JSONDecodeError, IndexError):
        pass

    return None
