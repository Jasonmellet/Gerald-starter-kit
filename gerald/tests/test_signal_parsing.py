import json

from app.schemas import SignalExtract
from app.constants import SignalType


def test_signal_extract_parses_valid_item():
    payload = {
        "signal_type": "NEEDS_PIPELINE",
        "confidence": 0.9,
        "signal_strength": 0.8,
        "evidence_text": "We need more qualified pipeline next quarter.",
        "extracted_pain_point": "Need more qualified pipeline",
        "extracted_goal": "Improve pipeline volume",
        "rationale": "Direct statement about pipeline needs.",
    }
    sig = SignalExtract.model_validate(payload)
    assert sig.signal_type == SignalType.NEEDS_PIPELINE
    assert sig.confidence == 0.9
    assert "pipeline" in sig.evidence_text.lower()

