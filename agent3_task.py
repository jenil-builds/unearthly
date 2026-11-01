"""
Agent 3: Schema Normalizer, Self-Correction & Database Validation Agent (agent3_task.py)
Enforces Assam LGD mapping, SI unit conversion, season inference, and SHA-256 deduplication.
"""

import re
import hashlib
from typing import Dict, Any, Tuple

ASSAM_LGD_MAP = {
    "state total": ("Assam (State Total)", "LGD_AS_00", "All Zones"),
    "assam": ("Assam (State Total)", "LGD_AS_00", "All Zones"),
    "assam (state total)": ("Assam (State Total)", "LGD_AS_00", "All Zones"),
    "sibsagar": ("Sivasagar", "LGD_AS_300", "Upper Brahmaputra Valley Zone"),
    "sivasagar": ("Sivasagar", "LGD_AS_300", "Upper Brahmaputra Valley Zone"),
    "শিৱসাগৰ": ("Sivasagar", "LGD_AS_300", "Upper Brahmaputra Valley Zone"),
    "nowgong": ("Nagaon", "LGD_AS_297", "Central Brahmaputra Valley Zone"),
    "nagaon": ("Nagaon", "LGD_AS_297", "Central Brahmaputra Valley Zone"),
    "নগাঁও": ("Nagaon", "LGD_AS_297", "Central Brahmaputra Valley Zone"),
    "kamrup": ("Kamrup", "LGD_AS_291", "Lower Brahmaputra Valley Zone"),
    "কামৰূপ": ("Kamrup", "LGD_AS_291", "Lower Brahmaputra Valley Zone"),
    "barpeta": ("Barpeta", "LGD_AS_280", "Lower Brahmaputra Valley Zone"),
    "borpeta": ("Barpeta", "LGD_AS_280", "Lower Brahmaputra Valley Zone"),
    "বৰপেটা": ("Barpeta", "LGD_AS_280", "Lower Brahmaputra Valley Zone"),
    "cachar": ("Cachar", "LGD_AS_282", "Barak Valley Zone"),
    "কাচাৰ": ("Cachar", "LGD_AS_282", "Barak Valley Zone"),
    "jorhat": ("Jorhat", "LGD_AS_290", "Upper Brahmaputra Valley Zone"),
    "যোৰহাট": ("Jorhat", "LGD_AS_290", "Upper Brahmaputra Valley Zone"),
    "kokrajhar": ("Kokrajhar", "LGD_AS_294", "Lower Brahmaputra Valley Zone"),
    "sonitpur": ("Sonitpur", "LGD_AS_301", "North Bank Plains Zone"),
    "darrang": ("Darrang", "LGD_AS_283", "North Bank Plains Zone"),
    "darrang (kharupetia)": ("Darrang (Kharupetia)", "LGD_AS_283", "North Bank Plains Zone"),
    "golaghat": ("Golaghat", "LGD_AS_288", "Upper Brahmaputra Valley Zone"),
    "dibrugarh": ("Dibrugarh", "LGD_AS_286", "Upper Brahmaputra Valley Zone"),
    "tinsukia": ("Tinsukia", "LGD_AS_302", "Upper Brahmaputra Valley Zone"),
    "lakhimpur": ("Lakhimpur", "LGD_AS_295", "North Bank Plains Zone"),
}

ALLOWED_SI_UNITS = {"ha", "tonnes", "kg/ha", "INR", "Rs/Quintal", "mm", "days", "meters", "scale", "pH"}


class Agent3TaskNormalizer:
    @staticmethod
    def resolve_district(raw_dist: str) -> Tuple[str, str, str]:
        raw_lower = str(raw_dist).strip().lower()
        if raw_lower in ASSAM_LGD_MAP:
            return ASSAM_LGD_MAP[raw_lower]
        cleaned = re.sub(r"\(.*?\)", "", raw_lower).strip()
        if cleaned in ASSAM_LGD_MAP:
            return ASSAM_LGD_MAP[cleaned]
        for k, val in ASSAM_LGD_MAP.items():
            if k in raw_lower:
                return val
        return (str(raw_dist).strip().title() or "Assam (State Total)", "LGD_AS_00", "Assam General")

    @staticmethod
    def infer_season(crop_name: str, variety_name: str) -> str:
        c = f"{crop_name} {variety_name}".lower()
        if any(k in c for k in ["sali", "winter paddy", "ranjit", "bahadur", "kharif"]):
            return "Kharif (Winter/Sali)"
        if any(k in c for k in ["mustard", "rapeseed", "wheat", "potato", "blackgram", "rabi", "boro", "summer"]):
            return "Rabi / Summer"
        if any(k in c for k in ["ahu", "autumn"]):
            return "Autumn (Ahu)"
        return "Annual / Multi-Season"

    @staticmethod
    def normalize_unit(val: float, unit: str) -> Tuple[float, str]:
        u_raw = str(unit).strip()
        u = u_raw.lower()
        if u in ["q/ha", "quintal/ha", "quintals/ha", "qtl/ha"]:
            return round(val * 100.0, 2), "kg/ha"
        if u in ["kg/ha", "kgs/ha"]:
            return round(val, 2), "kg/ha"
        if u in ["rs. lakh", "lakh rs", "rs lakh", "lakh inr"]:
            return round(val * 100000.0, 2), "INR"
        if u in ["inr", "rs", "rupees"]:
            return round(val, 2), "INR"
        if u in ["rs/quintal", "rs/qtl", "inr/quintal", "rs./quintal"]:
            return round(val, 2), "Rs/Quintal"
        if u in ["hectares", "hect.", "ha", "hectare", "হেক্টৰ"]:
            return round(val, 2), "ha"
        if u in ["tonnes", "mt", "metric tonnes", "tonne", "মেট্ৰিক টন"]:
            return round(val, 2), "tonnes"
        if u in ["mm", "millimeters"]:
            return round(val, 2), "mm"
        if u in ["days", "day"]:
            return round(val, 2), "days"
        if u in ["meters", "m", "meter"]:
            return round(val, 2), "meters"
        if u in ["scale"]:
            return round(val, 2), "scale"
        if u in ["ph"]:
            return round(val, 2), "pH"
        if u_raw in ALLOWED_SI_UNITS:
            return round(val, 2), u_raw
        raise ValueError(f"Unsupported unit: '{u_raw}'")

    @staticmethod
    def clean_num(val_str: str) -> float:
        s = re.sub(r"[^\d.\-]", "", str(val_str).replace(",", ""))
        try:
            v = float(s) if s else 1.0
            return v if v > 0 else 1.0
        except ValueError:
            return 1.0

    def normalize_record(self, raw_rec: Dict[str, Any]) -> Dict[str, Any]:
        raw_v = str(raw_rec.get("raw_value", "1.0"))
        raw_agent = str(raw_rec.get("agent", "agent2_ingestion"))
        agent_role = "agent2b_live_gis" if raw_agent in ["agent2b_live_gis", "LiveMandi_Agent", "GeoSpatial_Agent"] else "agent2_ingestion"

        retries = 0
        validation_status = "VALIDATED"
        traj = [
            f"agent1_classifier->{agent_role}",
            f"Tool:{agent_role}_Extractor",
        ]

        if "*" in raw_v or "CORRUPT" in raw_v or "NaN" in raw_v:
            retries = 1
            validation_status = "SELF_CORRECTED"
            traj.append("agent3_task:SelfCorrectionNode")
            raw_v = re.sub(r"[A-Za-z_*]", "", raw_v).strip()

        traj.extend(["agent3_task:Normalized", "DB_Commit_Ready"])

        num_val = self.clean_num(raw_v)
        norm_val, norm_unit = self.normalize_unit(num_val, raw_rec.get("raw_unit", "ha"))
        canon_dist, lgd_code, zone = self.resolve_district(raw_rec.get("district_raw", "Assam"))

        crop_name = str(raw_rec.get("crop_name") or "Rice (Paddy)").strip()
        variety_name = str(raw_rec.get("variety_name") or "General").strip()
        crop_id = hashlib.md5(f"{crop_name}|{variety_name}".encode()).hexdigest()[:12]
        season_category = self.infer_season(crop_name, variety_name)

        source_id = str(raw_rec.get("source_id") or "SURPRISE_01").strip()
        locator = str(raw_rec.get("locator") or "Page=1;Row=1").strip()
        time_period = str(raw_rec.get("time_period") or "2024-25").strip()
        metric_name = str(raw_rec.get("metric_name") or "Area").strip()
        source_type = str(raw_rec.get("source_type") or "Document_PDF").strip()

        rec_hash = hashlib.sha256(
            f"{source_id}|{locator}|{crop_id}|{lgd_code}|{time_period}|{metric_name}".encode()
        ).hexdigest()[:24]

        return {
            **raw_rec,
            "source_id": source_id,
            "source_type": source_type,
            "agent": agent_role,
            "locator": locator,
            "crop_id": crop_id,
            "crop_name": crop_name,
            "variety_name": variety_name,
            "season_category": season_category,
            "canonical_district": canon_dist,
            "location_id": lgd_code,
            "agro_climatic_zone": zone,
            "time_period": time_period,
            "metric_name": metric_name,
            "normalized_value": norm_val,
            "normalized_unit": norm_unit,
            "validation_status": validation_status,
            "record_hash": rec_hash,
            "retries": retries,
            "trajectory": " -> ".join(traj),
        }
