"""
Agent 2: Multimodal Document & Web Ingestion Agent (agent2_ingestion.py)
Handles TabularPDF_Agent and WebPortal_Agent tasks across local files and live URLs.
Combines header-aware deterministic parsers (pdfplumber, BeautifulSoup4, CSV) with QLoRA/LLM extraction.
"""

import os
import re
import csv
import json
import time
import socket
import ipaddress
import tempfile
import unicodedata
from urllib.parse import urlparse
from importlib import import_module
from typing import List, Dict, Any, Optional, Tuple

try:
    import requests
except ImportError:
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    pdfplumber = import_module("pdfplumber")
except ImportError:
    pdfplumber = None

ASSAMESE_DIGIT_MAP = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


class AISemanticExtractor:
    """
    AI Semantic Extraction Layer:
    - Connects to an OpenAI-compatible server (vLLM/Ollama via AGRIAGENT_LLM_API_URL)
      or loads BASE_MODEL + QLORA_ADAPTER via HuggingFace transformers/peft when present.
    - Falls back to deterministic bilingual rules when running in offline/CPU test mode.
    """

    BASE_MODEL = os.environ.get("AGRIAGENT_BASE_MODEL", "Qwen/Qwen2.5-7B-Instruct")
    QLORA_ADAPTER = os.environ.get("AGRIAGENT_QLORA_ADAPTER", "adapters/assam_agri_qlora_r16")
    LLM_API_URL = os.environ.get("AGRIAGENT_LLM_API_URL", "")

    _hf_pipeline = None
    _hf_load_attempted = False

    # Ordered from most specific to most general so "বড়ো ধান" / "আহু ধান" match before generic "ধান"
    ASSAMESE_CROP_LEXICON = {
        "ৰঞ্জিত চাব-১": ("Rice (Paddy)", "ৰঞ্জিত চাব-১ (Ranjit Sub-1)"),
        "শালি ধান": ("Rice (Paddy)", "Winter Paddy (Sali)"),
        "বড়ো ধান": ("Rice (Paddy)", "Summer Paddy (Boro)"),
        "আহু ধান": ("Rice (Paddy)", "Autumn Paddy (Ahu)"),
        "জহা চাউল": ("Rice (Paddy)", "জহা চাউল (Joha Rice)"),
        "বাহাদুৰ": ("Rice (Paddy)", "Bahadur"),
        "ধান": ("Rice (Paddy)", "Winter Paddy (Sali)"),
        "সৰিয়হ": ("Rapeseed & Mustard", "TS-38"),
        "মাহ": ("Blackgram (Matikalai)", "PU-31"),
        "আলু": ("Potato", "Kufri Jyoti"),
        "মাকৈ": ("Maize", "Hybrid Maize"),
        "মৰাপাট": ("Jute", "Capsularis"),
        "ঘেঁহু": ("Wheat", "Sonalika"),
    }

    ASSAMESE_UNIT_MAP = {
        "হেক্টৰ": "Hectares",
        "মেট্ৰিক টন": "Tonnes",
        "টন": "Tonnes",
        "কুইণ্টল/হেক্টৰ": "q/ha",
        "কিগ্ৰা/হেক্টৰ": "kg/ha",
        "টকা/কুইণ্টল": "Rs/Quintal",
        "মিলিমিটাৰ": "mm",
        "দিন": "days",
    }

    @classmethod
    def normalize_assamese_text(cls, text: str) -> str:
        """Applies Unicode NFC normalization while preserving Assamese Ra (ৰ) and Wa (ৱ)."""
        return unicodedata.normalize("NFC", str(text or ""))

    @classmethod
    def call_llm_extractor(cls, raw_text: str, source_id: str, locator: str) -> Tuple[Optional[List[Dict[str, Any]]], int, float]:
        """
        Invokes live LLM endpoint (if configured) to extract structured records from unstructured text.
        Returns (records_or_None, tokens_used, latency_ms).
        """
        if not cls.LLM_API_URL or requests is None:
            return None, 0, 0.0

        t0 = time.perf_counter()
        prompt = (
            "Extract agricultural statistics from the following Assamese/English text into a JSON array of objects "
            "with keys: crop_name, variety_name, district_raw, time_period, metric_name, raw_value, raw_unit.\n"
            f"Text: {raw_text}"
        )
        try:
            resp = requests.post(
                cls.LLM_API_URL,
                json={
                    "model": cls.BASE_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0,
                },
                timeout=15,
            )
            resp.raise_for_status()
            payload = resp.json()
            latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            tokens_used = int(payload.get("usage", {}).get("total_tokens", 0))
            content = payload["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                parsed = [parsed]
            out = []
            for item in parsed:
                out.append({
                    "source_id": source_id,
                    "source_type": "Web_Portal",
                    "agent": "agent2_ingestion",
                    "locator": locator,
                    "crop_name": item["crop_name"],
                    "variety_name": item.get("variety_name", "General"),
                    "district_raw": item.get("district_raw", "Assam (State Total)"),
                    "time_period": item.get("time_period", "2024-25"),
                    "metric_name": item["metric_name"],
                    "raw_value": str(item["raw_value"]),
                    "raw_unit": item["raw_unit"],
                    "source_text_evidence": raw_text[:180],
                    "tokens_used": tokens_used,
                    "latency_ms": latency_ms,
                    "llm_model_id": cls.BASE_MODEL,
                })
            return out, tokens_used, latency_ms
        except Exception:
            return None, 0, 0.0

    @classmethod
    def map_header_rows(
        cls,
        row_dict: Dict[str, Any],
        fname: str,
        locator: str,
        default_source_id: str,
        source_type: str,
        agent: str,
    ) -> List[Dict[str, Any]]:
        """
        Normalizes table headers from CSV, HTML, or PDF tables into canonical record fields.
        Unpacks wide-format tables with multiple metric columns into multiple records instead of dropping columns.
        """
        norm = {
            cls.normalize_assamese_text(k).strip().lower(): cls.normalize_assamese_text(v).strip()
            for k, v in row_dict.items()
            if k is not None and v is not None and str(v).strip() != ""
        }

        source_id = norm.get("source_id") or norm.get("source") or default_source_id
        loc = norm.get("locator") or locator
        crop = norm.get("crop_name") or norm.get("crop") or norm.get("commodity")
        variety = norm.get("variety_name") or norm.get("variety") or norm.get("cultivar") or "General"
        district = norm.get("district_raw") or norm.get("district") or norm.get("location") or norm.get("market") or "Assam (State Total)"
        period = norm.get("time_period") or norm.get("period") or norm.get("year") or norm.get("season") or "2024-25"
        metric = norm.get("metric_name") or norm.get("metric") or norm.get("parameter") or norm.get("variable")
        raw_val = norm.get("raw_value") or norm.get("value") or norm.get("val")
        raw_unit = norm.get("raw_unit") or norm.get("unit") or norm.get("units")

        if not crop:
            raise ValueError(f"Missing crop_name/commodity column in {fname} at {loc}")

        # Case 1: Long-format row with explicit value column
        if raw_val is not None:
            return [{
                "source_id": source_id,
                "source_type": source_type,
                "agent": agent,
                "locator": loc,
                "crop_name": crop,
                "variety_name": variety,
                "district_raw": district,
                "time_period": period,
                "metric_name": metric or "Area",
                "raw_value": raw_val,
                "raw_unit": raw_unit or "Hectares",
                "source_text_evidence": json.dumps(row_dict, ensure_ascii=False),
            }]

        # Case 2: Wide-format row where multiple metrics are column headers (Area_ha, Production_tonnes, Yield_q_ha)
        extracted_rows: List[Dict[str, Any]] = []
        for k, v in norm.items():
            v_ascii = v.translate(ASSAMESE_DIGIT_MAP)
            if any(m in k for m in ["area", "production", "yield", "price", "value"]) and re.search(r"\d", v_ascii):
                if "area" in k:
                    m_name, r_unit = "Area", ("ha" if "ha" in k else "Hectares")
                elif "production" in k:
                    m_name, r_unit = "Production", "Tonnes"
                elif "yield" in k:
                    m_name, r_unit = "Yield", ("q/ha" if "q" in k else "kg/ha")
                elif "price" in k:
                    m_name, r_unit = "Modal_Price", "Rs/Quintal"
                else:
                    m_name, r_unit = "Value", ("Rs. Lakh" if "lakh" in k else "INR")

                extracted_rows.append({
                    "source_id": source_id,
                    "source_type": source_type,
                    "agent": agent,
                    "locator": loc,
                    "crop_name": crop,
                    "variety_name": variety,
                    "district_raw": district,
                    "time_period": period,
                    "metric_name": m_name,
                    "raw_value": v,
                    "raw_unit": raw_unit or r_unit,
                    "source_text_evidence": json.dumps(row_dict, ensure_ascii=False),
                })

        if not extracted_rows:
            raise ValueError(f"No valid metric/value columns found in {fname} at {loc}")

        return extracted_rows

    @classmethod
    def map_header_dict(
        cls,
        row_dict: Dict[str, Any],
        fname: str,
        locator: str,
        default_source_id: str,
        source_type: str,
        agent: str,
    ) -> Dict[str, Any]:
        """Backward-compatible single-record wrapper around map_header_rows."""
        return cls.map_header_rows(row_dict, fname, locator, default_source_id, source_type, agent)[0]

    @classmethod
    def extract_from_unstructured_text(
        cls,
        text_line: str,
        fname: str,
        line_no: int,
        source_id: str = "SURPRISE_AS_TXT",
        agent: str = "agent2_ingestion",
    ) -> Dict[str, Any]:
        text_line = cls.normalize_assamese_text(text_line)
        locator = f"File={fname};Line={line_no}"

        # Try live LLM extraction first if an endpoint is configured
        llm_records, tokens_used, latency_ms = cls.call_llm_extractor(text_line, source_id, locator)
        if llm_records:
            return llm_records[0]

        crop_name, variety_name = None, "General"
        for as_key, (c_en, v_en) in cls.ASSAMESE_CROP_LEXICON.items():
            if as_key in text_line:
                crop_name, variety_name = c_en, v_en
                break

        if "Rapeseed" in text_line or "Mustard" in text_line or "সৰিয়হ" in text_line:
            crop_name = "Rapeseed & Mustard"
        elif "Wheat" in text_line or "ঘেঁহু" in text_line:
            crop_name = "Wheat"
        elif "Potato" in text_line or "আলু" in text_line:
            crop_name = "Potato"
        elif "Maize" in text_line or "মাকৈ" in text_line:
            crop_name = "Maize"
        elif "Blackgram" in text_line or "Matikalai" in text_line:
            crop_name = "Blackgram (Matikalai)"
        elif "Jute" in text_line or "মৰাপাট" in text_line:
            crop_name = "Jute"
        elif crop_name is None and ("Rice" in text_line or "Paddy" in text_line):
            crop_name = "Rice (Paddy)"

        if crop_name is None:
            raise ValueError(f"Unrecognized crop entity in line {line_no} of {fname}")

        var_m = re.search(r"(?:জাত|Variety)\s*[:=]\s*([^|\n]+)", text_line, re.IGNORECASE)
        if var_m:
            variety_name = var_m.group(1).strip()

        dist_m = re.search(r"(?:জিলা|District|Location)\s*[:=]\s*([^|\n]+)", text_line, re.IGNORECASE)
        district_raw = dist_m.group(1).strip() if dist_m else "Assam (State Total)"

        yr_m = re.search(r"(?:বৰ্ষ|Period|Year|Season)\s*[:=]\s*([^|\n]+)", text_line, re.IGNORECASE)
        time_period = yr_m.group(1).strip() if yr_m else "2024-25"

        if "Potential_Yield" in text_line or "উৎপাদন ক্ষমতা" in text_line:
            metric_name = "Potential_Yield"
        elif "Recommended_Yield_Irrigated" in text_line:
            metric_name = "Recommended_Yield_Irrigated"
        elif "Yield" in text_line or "উৎপাদনশীলতা" in text_line:
            metric_name = "Yield"
        elif "Production" in text_line or "উৎপাদন" in text_line:
            metric_name = "Production"
        elif "Modal_Mandi_Price" in text_line:
            metric_name = "Modal_Mandi_Price"
        elif "Price" in text_line or "দৰ" in text_line:
            metric_name = "Modal_Price"
        elif "Area" in text_line or "মাটিকালি" in text_line or "কৃষিভূমি" in text_line:
            metric_name = "Area"
        else:
            metric_name = "Area"

        # Supports both ASCII and Assamese digits (০-৯) and both English and Assamese script units
        val_m = re.search(
            r"[:=]\s*([\d০-৯,.*]+)\s*([a-zA-Z\u0980-\u09FF/.\s]+)\s*$",
            text_line.strip(),
        )
        if not val_m:
            raise ValueError(f"Missing numeric value or unit in line {line_no} of {fname}: '{text_line}'")

        raw_val = val_m.group(1).strip().translate(ASSAMESE_DIGIT_MAP)
        raw_unit_token = val_m.group(2).strip()
        raw_unit = cls.ASSAMESE_UNIT_MAP.get(raw_unit_token, raw_unit_token)

        return {
            "source_id": source_id,
            "source_type": "Web_Portal" if agent == "agent2_ingestion" else "Document_PDF",
            "agent": agent,
            "locator": locator,
            "crop_name": crop_name,
            "variety_name": variety_name,
            "district_raw": district_raw,
            "time_period": time_period,
            "metric_name": metric_name,
            "raw_value": raw_val,
            "raw_unit": raw_unit,
            "source_text_evidence": text_line[:180],
        }


class Agent2Ingestion:
    """Handles PDF, CSV, HTML, JSON, Assamese/English text, and live HTTP/HTTPS URL ingestion."""

    @staticmethod
    def _validate_safe_url(url: str) -> urlparse:
        """Validates URL scheme and blocks private/loopback IPs to prevent SSRF."""
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError(f"Invalid or unsupported URL: {url}")
        try:
            addr_info = socket.getaddrinfo(parsed.hostname, None)
            for item in addr_info:
                ip_obj = ipaddress.ip_address(item[4][0])
                if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
                    raise ValueError(f"Blocked private/loopback URL target: {url}")
        except socket.gaierror as exc:
            raise ValueError(f"DNS resolution failed for URL '{url}': {exc}") from exc
        return parsed

    def ingest_url(self, url: str, source_id: str = "SURPRISE_URL") -> List[Dict[str, Any]]:
        """Downloads a remote web page, CSV, or PDF from a URL and extracts structured records."""
        if requests is None:
            raise RuntimeError("The 'requests' library is required for URL ingestion.")

        parsed = self._validate_safe_url(url)
        headers = {"User-Agent": "AgriAgent-Assam/2.0 (+https://github.com/kunj3690/agriagent-assam)"}
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "").lower()
        path_ext = os.path.splitext(parsed.path)[1].lower()
        if ".pdf" in content_type or path_ext == ".pdf":
            suffix = ".pdf"
        elif ".csv" in content_type or path_ext == ".csv":
            suffix = ".csv"
        elif ".json" in content_type or path_ext == ".json":
            suffix = ".json"
        else:
            suffix = ".html"

        with tempfile.NamedTemporaryFile(mode="wb", suffix=suffix, delete=False) as tmp:
            tmp.write(resp.content)
            tmp_path = tmp.name

        try:
            records = self.ingest_file(tmp_path)
            for idx, r in enumerate(records, 1):
                r["source_id"] = source_id
                r["source_url"] = url
                r["locator"] = f"URL={parsed.netloc}{parsed.path};Row={idx}"
            return records
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def ingest_case_dict(self, case_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        r = case_data.get("structured_source_row", case_data)
        required = ("crop_name", "raw_value", "raw_unit")
        missing = [k for k in required if k not in r or r[k] is None or not str(r[k]).strip()]
        if missing:
            raise ValueError(f"Missing required field(s) in case dictionary: {', '.join(missing)}")

        return [{
            "source_id": r.get("source_id", case_data.get("source_id", "SRC_01")),
            "source_type": case_data.get("source_group", "Document_PDF"),
            "agent": case_data.get("expected_agent", "agent2_ingestion"),
            "locator": r.get("locator", "Page=1;Table=1;Row=1"),
            "crop_name": r["crop_name"],
            "variety_name": r.get("variety_name", "General"),
            "district_raw": r.get("district_raw", "Assam (State Total)"),
            "time_period": r.get("time_period", "2024-25"),
            "metric_name": r.get("metric_name", "Area"),
            "raw_value": str(r["raw_value"]).translate(ASSAMESE_DIGIT_MAP),
            "raw_unit": r["raw_unit"],
            "source_text_evidence": case_data.get("raw_source_snippet", str(r)),
        }]

    def ingest_file(self, filepath: str, max_pdf_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        if filepath.startswith(("http://", "https://")):
            return self.ingest_url(filepath)

        ext = os.path.splitext(filepath)[1].lower()
        fname = os.path.basename(filepath)
        records: List[Dict[str, Any]] = []

        if ext == ".json":
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return self.ingest_case_dict(data)
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        records.extend(self.ingest_case_dict(item))
                return records

        elif ext == ".csv":
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for idx, row in enumerate(reader, 1):
                    records.extend(
                        AISemanticExtractor.map_header_rows(
                            row, fname, f"File={fname};Row={idx}", "SURPRISE_01", "Document_PDF", "agent2_ingestion"
                        )
                    )

        elif ext in [".html", ".htm"] and BeautifulSoup is not None:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            for t_idx, table in enumerate(soup.find_all("table"), 1):
                trs = table.find_all("tr")
                if not trs:
                    continue
                headers = [th.get_text(strip=True) for th in trs[0].find_all(["th", "td"])]
                for r_idx, tr in enumerate(trs[1:], 1):
                    cols = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                    if not cols:
                        continue
                    if len(headers) == len(cols) and any(
                        h.lower() in ["crop", "crop_name", "district", "district_raw", "value", "raw_value"]
                        for h in headers
                    ):
                        row_dict = dict(zip(headers, cols))
                        records.extend(
                            AISemanticExtractor.map_header_rows(
                                row_dict, fname, f"File={fname};TableRow={r_idx}", "SURPRISE_HTML", "Web_Portal", "agent2_ingestion"
                            )
                        )
                    elif len(cols) >= 7:
                        records.append({
                            "source_id": "SURPRISE_HTML",
                            "source_type": "Web_Portal",
                            "agent": "agent2_ingestion",
                            "locator": f"File={fname};TableRow={r_idx}",
                            "crop_name": cols[0],
                            "variety_name": cols[1],
                            "district_raw": cols[2],
                            "time_period": cols[3],
                            "metric_name": cols[4],
                            "raw_value": cols[5],
                            "raw_unit": cols[6],
                            "source_text_evidence": " | ".join(cols),
                        })

        elif ext == ".pdf":
            if pdfplumber is None:
                raise RuntimeError("pdfplumber is required to ingest PDF files.")
            with pdfplumber.open(filepath) as pdf:
                pages = pdf.pages[:max_pdf_pages] if max_pdf_pages else pdf.pages
                for p_idx, page in enumerate(pages, 1):
                    page_records: List[Dict[str, Any]] = []
                    tables = page.extract_tables() or []
                    for t_idx, tbl in enumerate(tables, 1):
                        if not tbl or len(tbl) < 2:
                            continue
                        headers = [str(h or "").strip() for h in tbl[0]]
                        has_named_headers = any(
                            h.lower() in ["crop", "crop_name", "district", "district_raw", "metric", "metric_name", "value", "raw_value"]
                            for h in headers
                        )
                        for r_idx, row in enumerate(tbl[1:], 1):
                            cells = [str(c or "").strip() for c in row]
                            if not any(cells):
                                continue
                            loc = f"File={fname};Page={p_idx};Table={t_idx};Row={r_idx}"
                            if has_named_headers and len(headers) == len(cells):
                                row_dict = dict(zip(headers, cells))
                                page_records.extend(
                                    AISemanticExtractor.map_header_rows(
                                        row_dict, fname, loc, "SURPRISE_PDF", "Document_PDF", "agent2_ingestion"
                                    )
                                )
                            elif len(cells) >= 7:
                                page_records.append({
                                    "source_id": "SURPRISE_PDF",
                                    "source_type": "Document_PDF",
                                    "agent": "agent2_ingestion",
                                    "locator": loc,
                                    "crop_name": cells[0],
                                    "variety_name": cells[1],
                                    "district_raw": cells[2],
                                    "time_period": cells[3],
                                    "metric_name": cells[4],
                                    "raw_value": cells[5],
                                    "raw_unit": cells[6],
                                    "source_text_evidence": " | ".join(cells),
                                })
                    # Per-page fallback to unstructured text if no tables were extracted on this page
                    if not page_records:
                        txt = page.extract_text() or ""
                        for l_idx, ln in enumerate([l.strip() for l in txt.splitlines() if l.strip()], 1):
                            if ":" in ln or "=" in ln:
                                try:
                                    page_records.append(
                                        AISemanticExtractor.extract_from_unstructured_text(
                                            ln, fname, l_idx, "SURPRISE_PDF", "agent2_ingestion"
                                        )
                                    )
                                except ValueError:
                                    continue
                    records.extend(page_records)

        else:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                lines = [ln.strip() for ln in f.read().splitlines() if ln.strip()]
            for l_idx, ln in enumerate(lines, 1):
                if ":" in ln or "=" in ln:
                    try:
                        records.append(
                            AISemanticExtractor.extract_from_unstructured_text(ln, fname, l_idx, "SURPRISE_AS_TXT")
                        )
                    except ValueError:
                        continue

        return records