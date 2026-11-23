"""Zero-Fabrication Validator, Constrained AI LGD Disambiguator & AI Critic (ingestion/validator.py)."""
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from agent3_task import ALLOWED_SI_UNITS, ASSAM_LGD_MAP, Agent3TaskNormalizer
from ingestion.ai_runtime import AIRuntime
from ingestion.grounding import GroundingError, VerbatimGroundingGate
from ingestion.models import SourceRecord

VALID_LGD_CATALOG: Dict[str, Tuple[str, str]] = {}
for _canon_name, _lgd_code, _zone in ASSAM_LGD_MAP.values():
    if _lgd_code not in VALID_LGD_CATALOG:
        VALID_LGD_CATALOG[_lgd_code] = (_canon_name, _zone)

AGRONOMIC_BOUNDS: Dict[str, Tuple[float, float]] = {
    "pH": (2.0, 11.0), "kg/ha": (0.0, 50000.0), "Rs/Quintal": (0.0, 500000.0),
    "days": (0.0, 400.0), "mm": (0.0, 15000.0), "ha": (0.0, 1e8), "tonnes": (0.0, 1e9), "INR": (0.0, 1e12),
}

PERCENT_TOKEN_RE = re.compile(r"(%|percent|pct\b)", re.IGNORECASE)

LGD_DISAMBIGUATION_PROMPT = (
    "You are an Assam geography disambiguator for Indian agricultural records. "
    "Given a raw location/town/block name from Assam, map it ONLY to one of the official Assam LGD codes "
    "in the provided catalog, or return null if it cannot be reliably mapped to a district in Assam.\n"
    'Return ONLY JSON: {"location_id": "LGD_AS_XXX" | null, "reason": str}'
)

CRITIC_REPAIR_PROMPT = (
    "You are a strict Agricultural Data Critic. A record failed deterministic parsing or unit normalization. "
    "Inspect the verbatim_quote from the source document and determine if the raw_value or raw_unit can be "
    "cleanly repaired WITHOUT inventing digits or changing the physical dimension/meaning of the unit. "
    "NEVER coerce percentages ('%', 'percent'), ratios, or unsupported units into 'scale' or any other unit. "
    "The repaired raw_value MUST literally appear in verbatim_quote, and repaired raw_unit MUST be a direct "
    "synonym of the source unit from: "
    "Hectares, ha, Tonnes, MT, q/ha, t/ha, kg/ha, Rs. Lakh, INR, Rs/Quintal, mm, days, meters, scale, pH.\n"
    'If the unit is a percentage or cannot be safely repaired without changing meaning, set action="REJECT".\n'
    'Return ONLY JSON: {"action": "REPAIR" | "REJECT", "raw_value": str|null, "raw_unit": str|null, "reason": str}'
)


class ZeroFabricationValidator:
    def __init__(self, normalizer: Optional[Agent3TaskNormalizer] = None, ai_runtime: Optional[AIRuntime] = None, enable_ai_critic: bool = True, max_critic_calls_per_batch: int = 5) -> None:
        self.normalizer = normalizer or Agent3TaskNormalizer()
        self.ai = ai_runtime or AIRuntime()
        self.enable_ai_critic = enable_ai_critic
        self.max_critic_calls_per_batch = max_critic_calls_per_batch

    def _disambiguate_district_with_ai(self, district_raw: str, verbatim_quote: str) -> Tuple[Optional[Tuple[str, str, str]], int, str]:
        if not self.enable_ai_critic:
            return None, 0, ""
        catalog_summary = {code: name for code, (name, _) in sorted(VALID_LGD_CATALOG.items())}
        res = self.ai.call_json("agent3_task", LGD_DISAMBIGUATION_PROMPT, json.dumps({"district_raw": district_raw, "verbatim_quote": verbatim_quote[:300], "valid_lgd_catalog": catalog_summary}, ensure_ascii=False))
        if res.used_fallback or not isinstance(res.parsed_json, dict):
            return None, 0, ""
        chosen = str(res.parsed_json.get("location_id") or "").strip()
        if chosen in VALID_LGD_CATALOG:
            canon_name, zone = VALID_LGD_CATALOG[chosen]
            return (canon_name, chosen, zone), res.tokens_used, res.model_id
        return None, res.tokens_used, res.model_id

    @staticmethod
    def _is_forbidden_unit_coercion(rec: SourceRecord, rep_unit: str) -> bool:
        orig_u = str(rec.raw_unit or "").strip()
        orig_v = str(rec.raw_value or "").strip()
        if PERCENT_TOKEN_RE.search(orig_u) or PERCENT_TOKEN_RE.search(orig_v):
            return True
        if rep_unit.strip().lower() == "scale" and "scale" not in orig_u.lower() and "scale" not in rec.verbatim_quote.lower():
            return True
        return False

    def _critique_and_repair_with_ai(self, rec: SourceRecord, error_msg: str) -> Tuple[Optional[Tuple[str, str]], int, str]:
        if not self.enable_ai_critic:
            return None, 0, ""
        if PERCENT_TOKEN_RE.search(str(rec.raw_unit or "")) or PERCENT_TOKEN_RE.search(str(rec.raw_value or "")):
            return None, 0, ""
        res = self.ai.call_json("agent3_task", CRITIC_REPAIR_PROMPT, json.dumps({"error": error_msg, "raw_value": rec.raw_value, "raw_unit": rec.raw_unit, "metric_name": rec.metric_name, "verbatim_quote": rec.verbatim_quote[:400]}, ensure_ascii=False))
        if res.used_fallback or not isinstance(res.parsed_json, dict) or str(res.parsed_json.get("action", "")).upper() != "REPAIR":
            return None, res.tokens_used if not res.used_fallback else 0, res.model_id if not res.used_fallback else ""
        rep_val = str(res.parsed_json.get("raw_value") or "").strip()
        rep_unit = str(res.parsed_json.get("raw_unit") or "").strip()
        if not rep_val or not rep_unit or not VerbatimGroundingGate.value_in_quote(rep_val, rec.verbatim_quote) or self._is_forbidden_unit_coercion(rec, rep_unit):
            return None, res.tokens_used, res.model_id
        return (rep_val, rep_unit), res.tokens_used, res.model_id

    @staticmethod
    def _check_agronomic_bounds(norm_val: float, norm_unit: str) -> None:
        bounds = AGRONOMIC_BOUNDS.get(norm_unit)
        if bounds is not None and not (bounds[0] < norm_val <= bounds[1]):
            raise ValueError(f"Agronomic sanity bound violation: {norm_val} {norm_unit} outside ({bounds[0]}, {bounds[1]}]")

    def _to_raw_dict(self, rec: SourceRecord, raw_value: str, raw_unit: str) -> Dict[str, Any]:
        return {
            "source_id": rec.source_id, "source_url": rec.source_url, "source_type": rec.source_type,
            "agent": rec.extracting_agent, "locator": rec.locator, "crop_name": rec.crop_name,
            "variety_name": rec.variety_name, "district_raw": rec.district_raw, "time_period": rec.time_period,
            "metric_name": rec.metric_name, "raw_value": raw_value, "raw_unit": raw_unit,
            "source_text_evidence": rec.verbatim_quote, "fetched_at_utc": rec.fetched_at_utc,
            "llm_model_id": rec.llm_model_id, "tokens_used": rec.tokens_used, "latency_ms": rec.latency_ms,
        }

    def validate_record(self, rec: SourceRecord, source_text: Optional[str] = None, allow_critic: bool = True) -> Tuple[Dict[str, Any], int, str]:
        VerbatimGroundingGate.verify_record(rec, source_text=source_text)
        extra_tokens, critic_model, repaired_by_critic = 0, "", False
        raw_dict = self._to_raw_dict(rec, rec.raw_value, rec.raw_unit)
        try:
            norm = self.normalizer.normalize_record(raw_dict)
            self._check_agronomic_bounds(norm["normalized_value"], norm["normalized_unit"])
        except ValueError as err:
            if not allow_critic:
                raise
            repaired, tok, mod = self._critique_and_repair_with_ai(rec, str(err))
            extra_tokens += tok
            if mod: critic_model = mod
            if repaired is None:
                raise
            raw_dict = self._to_raw_dict(rec, repaired[0], repaired[1])
            norm = self.normalizer.normalize_record(raw_dict)
            self._check_agronomic_bounds(norm["normalized_value"], norm["normalized_unit"])
            repaired_by_critic = True

        if str(norm["location_id"]).startswith("LGD_AS_UNMAPPED_") and allow_critic:
            resolved, tok, mod = self._disambiguate_district_with_ai(rec.district_raw, rec.verbatim_quote)
            extra_tokens += tok
            if mod: critic_model = mod
            if resolved is not None:
                canon_dist, lgd_code, zone = resolved
                raw_dict["district_raw"] = canon_dist
                norm = self.normalizer.normalize_record(raw_dict)
                norm["canonical_district"], norm["location_id"], norm["agro_climatic_zone"] = canon_dist, lgd_code, zone
                norm["trajectory"] = norm["trajectory"].replace("agent3_task:Normalized", "agent3_task:AI_LGD_Disambiguated -> agent3_task:Normalized")

        if repaired_by_critic:
            norm["validation_status"] = "SELF_CORRECTED"
            norm["retries"] = max(int(norm.get("retries", 0)), 1)
            norm["trajectory"] = norm["trajectory"].replace("agent3_task:Normalized", "agent3_task:AI_Critic_Repaired -> agent3_task:Normalized")

        if norm["normalized_unit"] not in ALLOWED_SI_UNITS:
            raise ValueError(f"Disallowed normalized unit: {norm['normalized_unit']}")
        return norm, extra_tokens, critic_model

    def validate_batch(self, records: List[SourceRecord], source_text: Optional[str] = None) -> Tuple[List[Dict[str, Any]], List[str], int, Optional[str]]:
        valid, rejected, total_tokens, last_model = [], [], 0, None
        critic_calls_used = 0
        for idx, rec in enumerate(records, 1):
            total_tokens += int(rec.tokens_used or 0)
            if rec.llm_model_id and rec.llm_model_id != "deterministic_fallback":
                last_model = rec.llm_model_id
            can_call = critic_calls_used < self.max_critic_calls_per_batch
            try:
                norm, extra_tok, critic_mod = self.validate_record(rec, source_text=source_text, allow_critic=can_call)
                if extra_tok > 0 or critic_mod:
                    critic_calls_used += 1
                total_tokens += extra_tok
                if critic_mod: last_model = critic_mod
                valid.append(norm)
            except (GroundingError, ValueError) as exc:
                if can_call and not isinstance(exc, GroundingError):
                    critic_calls_used += 1
                rejected.append(f"Record #{idx} ({rec.locator}): {exc}")
        return valid, rejected, total_tokens, last_model
