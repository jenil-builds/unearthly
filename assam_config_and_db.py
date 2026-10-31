"""
MODULE 1: assam_config_and_db.py
Contains:
- Complete 15-Source Manifest for Team 3 (Assam)
- Deterministic Assam District LGD Alias Resolver & SI Unit Standardizer
- Pydantic Schemas for Constrained LLM Decoding
- SQLite Relational Database & Provenance Schema
"""

import re
import sqlite3
import hashlib
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

ASSAM_SOURCES_MANIFEST: List[Dict[str, Any]] = [
    {
        "source_id": "SRC_01",
        "name": "DES Assam - Ten Major Crops in Assam (2003-04 to 2012-13)",
        "url": "https://des.assam.gov.in/sites/default/files/swf_utility_folder/departments/ecostat_medhassu_in_oid_3/menu/document/ten_major_crops_1.pdf",
        "modality": "PDF",
        "period": "2003-04 to 2012-13",
        "assigned_agent": "TabularPDF_Agent",
        "status": "IMPLEMENTED",
        "limitation": "Series stops at 2012-13; multi-header table requires structured extraction"
    },
    {
        "source_id": "SRC_02",
        "name": "ICAR-IIRR - Released Rice Varieties and Hybrids",
        "url": "https://www.icar-iirr.org/3.ICAR-IIRR_Varietiesandhybrids_Available_for_Commercialization_through_Licensing.pdf",
        "modality": "PDF",
        "period": "1997-2013",
        "assigned_agent": "TabularPDF_Agent",
        "status": "IMPLEMENTED",
        "limitation": "National list; requires semantic filtering for Assam/NE ecology"
    },
    {
        "source_id": "SRC_03",
        "name": "ASAMB - Cold Storage Facilities List",
        "url": "https://asamb.assam.gov.in/sites/default/files/swf_utility_folder/departments/asamb_medhassu_in_oid_7/menu/information_and_services/cold_storage_under_asamb.pdf",
        "modality": "PDF",
        "period": "Current",
        "assigned_agent": "TabularPDF_Agent",
        "status": "IMPLEMENTED",
        "limitation": "Lists only ASAMB-owned facilities (18,000 MT total), excludes private units"
    },
    {
        "source_id": "SRC_04",
        "name": "Directorate of Agriculture Assam - Statistical Table 11(A).2",
        "url": "https://diragri.assam.gov.in/sites/default/files/swf_utility_folder/departments/diragri_medhassu_in_oid_4/portlet/level_2/11%28A%29.2.pdf",
        "modality": "PDF",
        "period": "Historical/Current",
        "assigned_agent": "TabularPDF_Agent",
        "status": "IMPLEMENTED",
        "limitation": "Multi-column statistical PDF with footnote markers"
    },
    {
        "source_id": "SRC_05",
        "name": "IP India - State-wise Registered GI of India",
        "url": "https://ipindia.gov.in/frontend/pdf/gi/registered/State_wise_Registered_GI_of_India.pdf",
        "modality": "PDF",
        "period": "Current",
        "assigned_agent": "TabularPDF_Agent",
        "status": "IMPLEMENTED",
        "limitation": "National list; requires filtering for Assam agricultural GIs"
    },
    {
        "source_id": "SRC_06",
        "name": "AAU - Package of Practices for Rabi Crops of Assam 2023",
        "url": "https://kvkkokrajhar.aau.ac.in/pop.php",
        "modality": "Web",
        "period": "2023",
        "assigned_agent": "WebPortal_Agent",
        "status": "IMPLEMENTED",
        "limitation": "Covers Rabi season only; potential agronomic yields"
    },
    {
        "source_id": "SRC_07",
        "name": "KVK Cachar (AAU) - Agromet Advisory Service Bulletins under GKMS",
        "url": "https://kvkcachar.aau.ac.in/agro.html",
        "modality": "Web",
        "period": "Rolling/Current",
        "assigned_agent": "WebPortal_Agent",
        "status": "IMPLEMENTED",
        "limitation": "District-specific to Cachar/Barak Valley"
    },
    {
        "source_id": "SRC_08",
        "name": "RKB Assam - Rice Knowledge Bank Factsheets",
        "url": "https://rkbassam.aau.ac.in/factsheets",
        "modality": "Web",
        "period": "Current",
        "assigned_agent": "WebPortal_Agent",
        "status": "IMPLEMENTED",
        "limitation": "Semi-structured HTML factsheets for rice management"
    },
    {
        "source_id": "SRC_09",
        "name": "Directorate of Agriculture Assam - Agricultural Statistics Portal",
        "url": "https://diragri.assam.gov.in/information-services/agricultural-statistics",
        "modality": "Web",
        "period": "Multi-year",
        "assigned_agent": "WebPortal_Agent",
        "status": "IMPLEMENTED",
        "limitation": "Index portal with links to sub-tables; SSL chain issues common"
    },
    {
        "source_id": "SRC_10",
        "name": "APEDA - Assam Agri Export State Profile",
        "url": "https://apeda.gov.in/Assam",
        "modality": "Web",
        "period": "Current",
        "assigned_agent": "WebPortal_Agent",
        "status": "IMPLEMENTED",
        "limitation": "State-level export cluster overview"
    },
    {
        "source_id": "SRC_11",
        "name": "AMIU (AAU Jorhat) - Live Market Intelligence Dashboard",
        "url": "https://amiu.aau.ac.in/",
        "modality": "Web_Dynamic",
        "period": "2023-2026 (Rolling/Current)",
        "assigned_agent": "LiveMandi_Agent",
        "status": "IMPLEMENTED",
        "limitation": "Live dashboard only; no bulk historical CSV download"
    },
    {
        "source_id": "SRC_12",
        "name": "AAU-IRRI APART Web GIS - Rice Area & Rice-Fallow Mapping",
        "url": "https://apartgis.aau.ac.in/",
        "modality": "Web_GIS",
        "period": "2017-18 onward",
        "assigned_agent": "GeoSpatial_Agent",
        "status": "METADATA_IMPLEMENTED_RASTER_PHASE3",
        "limitation": "Describes methodology; does not host direct raw GeoTIFF bulk link"
    },
    {
        "source_id": "SRC_13",
        "name": "RKB Assam - Web GIS Portal",
        "url": "https://rkbassam.aau.ac.in/web-gis",
        "modality": "Web_GIS",
        "period": "Current",
        "assigned_agent": "GeoSpatial_Agent",
        "status": "METADATA_IMPLEMENTED_RASTER_PHASE3",
        "limitation": "Interactive map viewer requiring WMS/layer metadata extraction"
    },
    {
        "source_id": "SRC_14",
        "name": "NBSS&LUP BHOOMI Geoportal - Assam Soil & Land Use",
        "url": "https://bhoomigeoportal-nbsslup.in/BHOOMI_StateWise/Assam.php",
        "modality": "Web_GIS",
        "period": "Current",
        "assigned_agent": "GeoSpatial_Agent",
        "status": "METADATA_IMPLEMENTED_RASTER_PHASE3",
        "limitation": "Geoportal layers require spatial query integration in Phase 3"
    },
    {
        "source_id": "SRC_15",
        "name": "NESDR & ASTEC Remote Sensing Datasets (Assam)",
        "url": "https://www.nesdr.gov.in/search/og_group_ref/148/type/dataset?sort_by=changed",
        "modality": "Web_GIS",
        "period": "Multi-year",
        "assigned_agent": "GeoSpatial_Agent",
        "status": "METADATA_IMPLEMENTED_RASTER_PHASE3",
        "limitation": "Includes https://astec.assam.gov.in/portlets/remote-sensing catalog"
    },
]

ASSAM_LGD_DISTRICT_MAP = {
    "state total": ("Assam (State Total)", "LGD_AS_00", "All Zones"),
    "assam": ("Assam (State Total)", "LGD_AS_00", "All Zones"),
    "sibsagar": ("Sivasagar", "LGD_AS_300", "Upper Brahmaputra Valley Zone"),
    "sivasagar": ("Sivasagar", "LGD_AS_300", "Upper Brahmaputra Valley Zone"),
    "nowgong": ("Nagaon", "LGD_AS_297", "Central Brahmaputra Valley Zone"),
    "nagaon": ("Nagaon", "LGD_AS_297", "Central Brahmaputra Valley Zone"),
    "kamrup": ("Kamrup", "LGD_AS_291", "Lower Brahmaputra Valley Zone"),
    "kamrup metro": ("Kamrup Metropolitan", "LGD_AS_618", "Lower Brahmaputra Valley Zone"),
    "borpeta": ("Barpeta", "LGD_AS_280", "Lower Brahmaputra Valley Zone"),
    "barpeta": ("Barpeta", "LGD_AS_280", "Lower Brahmaputra Valley Zone"),
    "cachar": ("Cachar", "LGD_AS_282", "Barak Valley Zone"),
    "jorhat": ("Jorhat", "LGD_AS_290", "Upper Brahmaputra Valley Zone"),
    "kokrajhar": ("Kokrajhar", "LGD_AS_294", "Lower Brahmaputra Valley Zone"),
    "sonitpur": ("Sonitpur", "LGD_AS_301", "North Bank Plains Zone"),
    "darrang": ("Darrang", "LGD_AS_283", "North Bank Plains Zone"),
    "golaghat": ("Golaghat", "LGD_AS_288", "Upper Brahmaputra Valley Zone"),
    "kharupetia": ("Darrang (Kharupetia)", "LGD_AS_283", "North Bank Plains Zone"),
    "singimari": ("Kamrup (Singimari)", "LGD_AS_291", "Lower Brahmaputra Valley Zone"),
    "chenijan": ("Jorhat (Chenijan)", "LGD_AS_290", "Upper Brahmaputra Valley Zone"),
    "byrnihat": ("Kamrup Metro (Byrnihat)", "LGD_AS_618", "Lower Brahmaputra Valley Zone"),
}

def clean_indian_number(val_str: Any) -> Optional[float]:
    if val_str is None:
        return None
    if isinstance(val_str, (int, float)):
        return float(val_str)
    cleaned = re.sub(r"[^\d.\-]", "", str(val_str).replace(",", ""))
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None

def resolve_assam_district(raw_name: str) -> Dict[str, str]:
    key = raw_name.strip().lower()
    if key in ASSAM_LGD_DISTRICT_MAP:
        canon, lgd, zone = ASSAM_LGD_DISTRICT_MAP[key]
        return {"canonical_name": canon, "lgd_code": lgd, "agro_climatic_zone": zone}
    return {"canonical_name": raw_name.strip().title(), "lgd_code": "LGD_AS_UNK", "agro_climatic_zone": "Assam General"}

def standardize_unit(value: float, unit: str) -> Dict[str, Any]:
    u = unit.strip().lower()
    if u in ["q/ha", "quintal/ha", "quintals/ha"]:
        return {"normalized_value": round(value * 100.0, 2), "normalized_unit": "kg/ha"}
    if u in ["rs. lakh", "lakh rs", "rs lakh"]:
        return {"normalized_value": round(value * 100000.0, 2), "normalized_unit": "INR"}
    if u in ["hectares", "hect.", "ha"]:
        return {"normalized_value": round(value, 2), "normalized_unit": "ha"}
    if u in ["tonnes", "mt", "metric tonnes"]:
        return {"normalized_value": round(value, 2), "normalized_unit": "tonnes"}
    return {"normalized_value": value, "normalized_unit": unit}

class ExtractedFactItem(BaseModel):
    crop_name: str = Field(description="Canonical crop or commodity name")
    variety_name: Optional[str] = Field(default="General", description="Specific crop variety or hybrid")
    season: Optional[str] = Field(default="Annual", description="Kharif, Rabi, Autumn, Winter, Summer")
    district_raw: str = Field(description="District or facility location as stated in source")
    time_period: str = Field(description="Fiscal year, release year, or observation date")
    metric_name: str = Field(description="Metric type e.g. Area, Production, Yield, Cold_Storage_Capacity")
    raw_value: str = Field(description="Exact numeric string from source before normalization")
    raw_unit: str = Field(description="Unit as written in source")
    source_location: str = Field(description="Page, Table, Row or URL XPath")

class AgentExtractionPayload(BaseModel):
    source_id: str
    extracting_agent: str
    records: List[ExtractedFactItem]
    notes: str

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS dim_sources (
    source_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    modality TEXT NOT NULL,
    period_of_info TEXT,
    assigned_agent TEXT NOT NULL,
    implementation_status TEXT NOT NULL,
    known_limitations TEXT
);

CREATE TABLE IF NOT EXISTS extraction_runs (
    run_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    extracting_agent TEXT NOT NULL,
    llm_model_used TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    retry_count INTEGER DEFAULT 0,
    manual_intervention_used INTEGER DEFAULT 0,
    status TEXT NOT NULL,
    error_message TEXT,
    FOREIGN KEY (source_id) REFERENCES dim_sources(source_id)
);

CREATE TABLE IF NOT EXISTS dim_locations (
    location_id TEXT PRIMARY KEY,
    canonical_district_name TEXT NOT NULL,
    agro_climatic_zone TEXT NOT NULL,
    state_name TEXT DEFAULT 'Assam'
);

CREATE TABLE IF NOT EXISTS dim_crops (
    crop_id TEXT PRIMARY KEY,
    crop_name TEXT NOT NULL,
    variety_name TEXT NOT NULL,
    season TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_agricultural_records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_hash TEXT UNIQUE NOT NULL,
    source_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    extracting_agent TEXT NOT NULL,
    source_location TEXT NOT NULL,
    location_id TEXT NOT NULL,
    crop_id TEXT NOT NULL,
    time_period TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    raw_value_text TEXT NOT NULL,
    raw_unit TEXT NOT NULL,
    normalized_value REAL,
    normalized_unit TEXT NOT NULL,
    validation_status TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES dim_sources(source_id),
    FOREIGN KEY (run_id) REFERENCES extraction_runs(run_id),
    FOREIGN KEY (location_id) REFERENCES dim_locations(location_id),
    FOREIGN KEY (crop_id) REFERENCES dim_crops(crop_id)
);
"""

def init_database(db_path: str = "assam_agri_phase2.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_SQL)
    cur = conn.cursor()
    for src in ASSAM_SOURCES_MANIFEST:
        cur.execute("""
            INSERT OR REPLACE INTO dim_sources 
            (source_id, source_name, source_url, modality, period_of_info, assigned_agent, implementation_status, known_limitations)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            src["source_id"], src["name"], src["url"], src["modality"],
            src["period"], src["assigned_agent"], src["status"], src["limitation"]
        ))
    conn.commit()
    return conn
