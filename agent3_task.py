"""
Agent 3: Schema Normalizer, Self-Correction & Database Validation Agent (agent3_task.py)
Enforces 35-district Assam LGD mapping, SI unit conversion, season inference, and SHA-256 deduplication.
"""

import re
import hashlib
from typing import Dict, Any, Tuple

ASSAMESE_DIGIT_MAP = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

ASSAM_LGD_MAP = {
    # State Aggregate
    "state total": ("Assam (State Total)", "LGD_AS_00", "All Zones"),
    "assam": ("Assam (State Total)", "LGD_AS_00", "All Zones"),
    "assam (state total)": ("Assam (State Total)", "LGD_AS_00", "All Zones"),
    "অসম": ("Assam (State Total)", "LGD_AS_00", "All Zones"),
    # 35 Districts of Assam (English, Historical & Assamese Script)
    "baksa": ("Baksa", "LGD_AS_616", "Lower Brahmaputra Valley Zone"),
    "বাক্সা": ("Baksa", "LGD_AS_616", "Lower Brahmaputra Valley Zone"),
    "bajali": ("Bajali", "LGD_AS_739", "Lower Brahmaputra Valley Zone"),
    "বজালী": ("Bajali", "LGD_AS_739", "Lower Brahmaputra Valley Zone"),
    "barpeta": ("Barpeta", "LGD_AS_280", "Lower Brahmaputra Valley Zone"),
    "borpeta": ("Barpeta", "LGD_AS_280", "Lower Brahmaputra Valley Zone"),
    "বৰপেটা": ("Barpeta", "LGD_AS_280", "Lower Brahmaputra Valley Zone"),
    "biswanath": ("Biswanath", "LGD_AS_705", "North Bank Plains Zone"),
    "বিশ্বনাথ": ("Biswanath", "LGD_AS_705", "North Bank Plains Zone"),
    "bongaigaon": ("Bongaigaon", "LGD_AS_281", "Lower Brahmaputra Valley Zone"),
    "বঙাইগাঁও": ("Bongaigaon", "LGD_AS_281", "Lower Brahmaputra Valley Zone"),
    "cachar": ("Cachar", "LGD_AS_282", "Barak Valley Zone"),
    "কাচাৰ": ("Cachar", "LGD_AS_282", "Barak Valley Zone"),
    "charaideo": ("Charaideo", "LGD_AS_708", "Upper Brahmaputra Valley Zone"),
    "চৰাইদেউ": ("Charaideo", "LGD_AS_708", "Upper Brahmaputra Valley Zone"),
    "chirang": ("Chirang", "LGD_AS_612", "Lower Brahmaputra Valley Zone"),
    "চিৰাং": ("Chirang", "LGD_AS_612", "Lower Brahmaputra Valley Zone"),
    "darrang": ("Darrang", "LGD_AS_283", "North Bank Plains Zone"),
    "darrang (kharupetia)": ("Darrang (Kharupetia)", "LGD_AS_283", "North Bank Plains Zone"),
    "দৰং": ("Darrang", "LGD_AS_283", "North Bank Plains Zone"),
    "dhemaji": ("Dhemaji", "LGD_AS_284", "North Bank Plains Zone"),
    "ধেমাজি": ("Dhemaji", "LGD_AS_284", "North Bank Plains Zone"),
    "dhubri": ("Dhubri", "LGD_AS_285", "Lower Brahmaputra Valley Zone"),
    "ধুবুৰী": ("Dhubri", "LGD_AS_285", "Lower Brahmaputra Valley Zone"),
    "dibrugarh": ("Dibrugarh", "LGD_AS_286", "Upper Brahmaputra Valley Zone"),
    "ডিব্ৰুগড়": ("Dibrugarh", "LGD_AS_286", "Upper Brahmaputra Valley Zone"),
    "dima hasao": ("Dima Hasao", "LGD_AS_299", "Hill Zone"),
    "north cachar hills": ("Dima Hasao", "LGD_AS_299", "Hill Zone"),
    "ডিমা হাছাও": ("Dima Hasao", "LGD_AS_299", "Hill Zone"),
    "goalpara": ("Goalpara", "LGD_AS_287", "Lower Brahmaputra Valley Zone"),
    "গোৱালপাৰা": ("Goalpara", "LGD_AS_287", "Lower Brahmaputra Valley Zone"),
    "golaghat": ("Golaghat", "LGD_AS_288", "Upper Brahmaputra Valley Zone"),
    "গোলাঘাট": ("Golaghat", "LGD_AS_288", "Upper Brahmaputra Valley Zone"),
    "hailakandi": ("Hailakandi", "LGD_AS_289", "Barak Valley Zone"),
    "হাইলাকান্দি": ("Hailakandi", "LGD_AS_289", "Barak Valley Zone"),
    "hojai": ("Hojai", "LGD_AS_709", "Central Brahmaputra Valley Zone"),
    "হোজাই": ("Hojai", "LGD_AS_709", "Central Brahmaputra Valley Zone"),
    "jorhat": ("Jorhat", "LGD_AS_290", "Upper Brahmaputra Valley Zone"),
    "যোৰহাট": ("Jorhat", "LGD_AS_290", "Upper Brahmaputra Valley Zone"),
    "kamrup": ("Kamrup", "LGD_AS_291", "Lower Brahmaputra Valley Zone"),
    "কামৰূপ": ("Kamrup", "LGD_AS_291", "Lower Brahmaputra Valley Zone"),
    "kamrup metropolitan": ("Kamrup Metropolitan", "LGD_AS_618", "Lower Brahmaputra Valley Zone"),
    "kamrup (metro)": ("Kamrup Metropolitan", "LGD_AS_618", "Lower Brahmaputra Valley Zone"),
    "guwahati": ("Kamrup Metropolitan", "LGD_AS_618", "Lower Brahmaputra Valley Zone"),
    "কামৰূপ মহানগৰ": ("Kamrup Metropolitan", "LGD_AS_618", "Lower Brahmaputra Valley Zone"),
    "karbi anglong": ("Karbi Anglong", "LGD_AS_292", "Hill Zone"),
    "কাৰ্বি আংলং": ("Karbi Anglong", "LGD_AS_292", "Hill Zone"),
    "karimganj": ("Karimganj", "LGD_AS_293", "Barak Valley Zone"),
    "sribhumi": ("Karimganj", "LGD_AS_293", "Barak Valley Zone"),
    "কৰিমগঞ্জ": ("Karimganj", "LGD_AS_293", "Barak Valley Zone"),
    "kokrajhar": ("Kokrajhar", "LGD_AS_294", "Lower Brahmaputra Valley Zone"),
    "কোকৰাঝাৰ": ("Kokrajhar", "LGD_AS_294", "Lower Brahmaputra Valley Zone"),
    "lakhimpur": ("Lakhimpur", "LGD_AS_295", "North Bank Plains Zone"),
    "লখিমপুৰ": ("Lakhimpur", "LGD_AS_295", "North Bank Plains Zone"),
    "majuli": ("Majuli", "LGD_AS_706", "Upper Brahmaputra Valley Zone"),
    "মাজুলী": ("Majuli", "LGD_AS_706", "Upper Brahmaputra Valley Zone"),
    "morigaon": ("Morigaon", "LGD_AS_296", "Central Brahmaputra Valley Zone"),
    "marigaon": ("Morigaon", "LGD_AS_296", "Central Brahmaputra Valley Zone"),
    "মৰিগাঁও": ("Morigaon", "LGD_AS_296", "Central Brahmaputra Valley Zone"),
    "nowgong": ("Nagaon", "LGD_AS_297", "Central Brahmaputra Valley Zone"),
    "nagaon": ("Nagaon", "LGD_AS_297", "Central Brahmaputra Valley Zone"),
    "নগাঁও": ("Nagaon", "LGD_AS_297", "Central Brahmaputra Valley Zone"),
    "nalbari": ("Nalbari", "LGD_AS_298", "Lower Brahmaputra Valley Zone"),
    "নলবাৰী": ("Nalbari", "LGD_AS_298", "Lower Brahmaputra Valley Zone"),
    "sibsagar": ("Sivasagar", "LGD_AS_300", "Upper Brahmaputra Valley Zone"),
    "sivasagar": ("Sivasagar", "LGD_AS_300", "Upper Brahmaputra Valley Zone"),
    "শিৱসাগৰ": ("Sivasagar", "LGD_AS_300", "Upper Brahmaputra Valley Zone"),
    "sonitpur": ("Sonitpur", "LGD_AS_301", "North Bank Plains Zone"),
    "শোণিতপুৰ": ("Sonitpur", "LGD_AS_301", "North Bank Plains Zone"),
    "south salmara-mankachar": ("South Salmara-Mankachar", "LGD_AS_707", "Lower Brahmaputra Valley Zone"),
    "south salmara": ("South Salmara-Mankachar", "LGD_AS_707", "Lower Brahmaputra Valley Zone"),
    "দক্ষিণ শালমাৰা-মানকাচৰ": ("South Salmara-Mankachar", "LGD_AS_707", "Lower Brahmaputra Valley Zone"),
    "tamulpur": ("Tamulpur", "LGD_AS_756", "Lower Brahmaputra Valley Zone"),
    "তামুলপুৰ": ("Tamulpur", "LGD_AS_756", "Lower Brahmaputra Valley Zone"),
    "tinsukia": ("Tinsukia", "LGD_AS_302", "Upper Brahmaputra Valley Zone"),
    "তিনিচুকীয়া": ("Tinsukia", "LGD_AS_302", "Upper Brahmaputra Valley Zone"),
    "udalguri": ("Udalguri", "LGD_AS_617", "North Bank Plains Zone"),
    "ওদালগুৰি": ("Udalguri", "LGD_AS_617", "North Bank Plains Zone"),
    "west karbi anglong": ("West Karbi Anglong", "LGD_AS_710", "Hill Zone"),
    "পশ্চিম কাৰ্বি আংলং": ("West Karbi Anglong", "LGD_AS_710", "Hill Zone"),
}

ALLOWED_SI_UNITS = {"ha", "tonnes", "kg/ha", "INR", "Rs/Quintal", "mm", "days", "meters", "scale", "pH"}


class Agent3TaskNormalizer:
    @staticmethod
    def resolve_district(raw_dist: str) -> Tuple[str, str, str]:
        raw_str = str(raw_dist or "").strip()
        if not raw_str:
            return ("Assam (State Total)", "LGD_AS_00", "All Zones")

        raw_lower = raw_str.lower()
        if raw_lower in ASSAM_LGD_MAP:
            return ASSAM_LGD_MAP[raw_lower]

        cleaned = re.sub(r"\(.*?\)", "", raw_lower).strip()
        if cleaned in ASSAM_LGD_MAP:
            return ASSAM_LGD_MAP[cleaned]

        # Match longest keys first so "west karbi anglong" or "kamrup (metro)" match before "karbi anglong" or "kamrup"
        for k in sorted(ASSAM_LGD_MAP.keys(), key=len, reverse=True):
            if k in raw_lower:
                return ASSAM_LGD_MAP[k]

        # Never overwrite LGD_AS_00 (Assam State Total) when an unmapped district name appears
        canon_title = raw_str.title()
        fallback_code = f"LGD_AS_UNMAPPED_{hashlib.md5(canon_title.encode()).hexdigest()[:4].upper()}"
        return (canon_title, fallback_code, "Assam General")

    @staticmethod
    def infer_season(crop_name: str, variety_name: str) -> str:
        c = f"{crop_name} {variety_name}".lower()
        if any(k in c for k in ["ahu", "autumn", "আহু"]):
            return "Autumn (Ahu)"
        if any(k in c for k in ["boro", "summer", "বড়ো", "mustard", "rapeseed", "wheat", "potato", "blackgram", "rabi"]):
            return "Rabi / Summer"
        if any(k in c for k in ["sali", "winter paddy", "ranjit", "bahadur", "kharif", "শালি", "ৰঞ্জিত"]):
            return "Kharif (Winter/Sali)"
        return "Annual / Multi-Season"

    @staticmethod
    def normalize_unit(val: float, unit: str) -> Tuple[float, str]:
        u_raw = str(unit).strip()
        u = u_raw.lower()
        if u in ["q/ha", "quintal/ha", "quintals/ha", "qtl/ha", "কুইণ্টল/হেক্টৰ"]:
            return round(val * 100.0, 2), "kg/ha"
        if u in ["kg/ha", "kgs/ha", "কিগ্ৰা/হেক্টৰ"]:
            return round(val, 2), "kg/ha"
        if u in ["rs. lakh", "lakh rs", "rs lakh", "lakh inr"]:
            return round(val * 100000.0, 2), "INR"
        if u in ["inr", "rs", "rupees", "টকা"]:
            return round(val, 2), "INR"
        if u in ["rs/quintal", "rs/qtl", "inr/quintal", "rs./quintal", "টকা/কুইণ্টল"]:
            return round(val, 2), "Rs/Quintal"
        if u in ["hectares", "hect.", "ha", "hectare", "হেক্টৰ"]:
            return round(val, 2), "ha"
        if u in ["tonnes", "mt", "metric tonnes", "tonne", "মেট্ৰিক টন", "টন"]:
            return round(val, 2), "tonnes"
        if u in ["mm", "millimeters", "মিলিমিটাৰ"]:
            return round(val, 2), "mm"
        if u in ["days", "day", "দিন"]:
            return round(val, 2), "days"
        if u in ["meters", "m", "meter", "মিটাৰ"]:
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
        s_ascii = str(val_str or "").translate(ASSAMESE_DIGIT_MAP).replace(",", "").strip()
        # Handle numeric ranges like "100-150" by computing midpoint
        range_m = re.match(r"^(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)$", s_ascii)
        if range_m:
            v = (float(range_m.group(1)) + float(range_m.group(2))) / 2.0
            if v <= 0:
                raise ValueError(f"Non-positive range value: '{val_str}'")
            return v

        s = re.sub(r"[^\d.\-]", "", s_ascii)
        if not s:
            raise ValueError(f"Cannot parse numeric value from: '{val_str}'")
        v = float(s)
        if v <= 0:
            raise ValueError(f"Numeric value must be > 0 (got {v} from '{val_str}')")
        return v

    def normalize_record(self, raw_rec: Dict[str, Any]) -> Dict[str, Any]:
        if "raw_value" not in raw_rec or raw_rec["raw_value"] is None:
            raise ValueError("Missing required 'raw_value' in record")

        raw_v = str(raw_rec["raw_value"]).translate(ASSAMESE_DIGIT_MAP)
        raw_agent = str(raw_rec.get("agent", "agent2_ingestion"))
        agent_role = (
            "agent2b_live_gis"
            if raw_agent in ["agent2b_live_gis", "LiveMandi_Agent", "GeoSpatial_Agent"]
            else "agent2_ingestion"
        )

        retries = 0
        validation_status = "VALIDATED"
        traj = [
            f"agent1_classifier->{agent_role}",
            f"Tool:{agent_role}_Extractor",
        ]

        if "*" in raw_v or "CORRUPT" in raw_v or "NaN" in raw_v or "#" in raw_v:
            retries = 1
            validation_status = "SELF_CORRECTED"
            traj.append("agent3_task:SelfCorrectionNode")
            raw_v = re.sub(r"[A-Za-z_*#]", "", raw_v).strip()

        traj.extend(["agent3_task:Normalized", "DB_Commit_Ready"])

        num_val = self.clean_num(raw_v)
        norm_val, norm_unit = self.normalize_unit(num_val, raw_rec.get("raw_unit", "ha"))
        canon_dist, lgd_code, zone = self.resolve_district(raw_rec.get("district_raw", "Assam (State Total)"))

        crop_name = str(raw_rec.get("crop_name") or "").strip()
        if not crop_name:
            raise ValueError("Missing required 'crop_name' in record")

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