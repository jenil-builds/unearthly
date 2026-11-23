"""Verbatim Span Grounding Gate (ingestion/grounding.py)."""
import re
import unicodedata
from typing import Optional

from agent3_task import ASSAMESE_DIGIT_MAP
from ingestion.models import SourceRecord


class GroundingError(ValueError):
    """Raised when a SourceRecord fails zero-fabrication or verbatim grounding verification."""


REQUIRED_RECORD_FIELDS = (
    "source_id", "source_url", "locator", "crop_name", "district_raw",
    "time_period", "metric_name", "raw_value", "raw_unit", "verbatim_quote", "fetched_at_utc",
)


def _norm_text(s: str) -> str:
    nfc = unicodedata.normalize("NFC", str(s or "")).translate(ASSAMESE_DIGIT_MAP)
    return re.sub(r"\s+", " ", nfc).strip()


def _digits_and_dot(s: str) -> str:
    return re.sub(r"[^\d.\-]", "", _norm_text(s))


def _token_boundary_match(needle: str, haystack: str) -> bool:
    if not needle or not haystack:
        return False
    pattern = r"(?<!\d)(?<!\d\.)" + re.escape(needle) + r"(?!\d)(?!\.\d)"
    return re.search(pattern, haystack) is not None


class VerbatimGroundingGate:
    @staticmethod
    def value_in_quote(raw_value: str, verbatim_quote: str) -> bool:
        val_norm = _norm_text(raw_value)
        quote_norm = _norm_text(verbatim_quote)
        if not val_norm or not quote_norm:
            return False
        if _token_boundary_match(val_norm, quote_norm):
            return True
        val_no_comma = val_norm.replace(",", "")
        quote_no_comma = quote_norm.replace(",", "")
        if _token_boundary_match(val_no_comma, quote_no_comma):
            return True
        num_core = _digits_and_dot(val_norm)
        return bool(num_core and _token_boundary_match(num_core, quote_no_comma))

    @classmethod
    def verify_record(cls, rec: SourceRecord, source_text: Optional[str] = None) -> None:
        missing = [f for f in REQUIRED_RECORD_FIELDS if not getattr(rec, f, None) or not str(getattr(rec, f)).strip()]
        if missing:
            raise GroundingError(f"Missing mandatory source-of-truth field(s): {', '.join(missing)}")
        if not cls.value_in_quote(rec.raw_value, rec.verbatim_quote):
            raise GroundingError(f"Ungrounded raw_value '{rec.raw_value}' not found in verbatim_quote '{rec.verbatim_quote[:100]}'")
        if source_text is not None and not rec.is_structured_table:
            if _norm_text(rec.verbatim_quote) not in _norm_text(source_text):
                raise GroundingError(f"Fabricated verbatim_quote not found in fetched source text: '{rec.verbatim_quote[:100]}'")
