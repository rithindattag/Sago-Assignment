from __future__ import annotations

from typing import Any, Dict, List


def decide_reengage(signals: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_score = 0.0
    descriptions: List[str] = []

    for signal in signals:
        score = float(signal.get("score", 0))
        total_score += score
        description = str(signal.get("description", "")).strip()
        if description:
            descriptions.append(description)

    should_reengage = total_score >= 70
    confidence = max(0.0, min(1.0, total_score / 100.0))

    if descriptions:
        reason = (
            f"Signals observed: {', '.join(descriptions[:3])}. "
            f"Total score is {int(total_score)} and the threshold is 70."
        )
    else:
        reason = (
            f"Total score is {int(total_score)} and the threshold is 70. "
            "No signal descriptions were provided."
        )

    return {
        "should_reengage": should_reengage,
        "confidence": confidence,
        "reason": reason,
    }
