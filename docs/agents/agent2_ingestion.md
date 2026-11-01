# Agent Card: `agent2_ingestion` (`Agent2Ingestion` & `AISemanticExtractor`)

* **Module File:** `agent2_ingestion.py`
* **Logical Domain Roles:** Consolidates `TabularPDF_Agent` (`Document_PDF`) and `WebPortal_Agent` (`Web_Portal`).
* **Assigned Sources:**
  * **Document PDFs (`SRC_01`–`SRC_05`):** DES Assam *Ten Major Crops* (`SRC_01`), ICAR-IIRR *Rice Varieties* (`SRC_02`), ASAMB *Cold Storage List* (`SRC_03`), DirAgri *Table 11(A).2* (`SRC_04`), IP India *GI Registry* (`SRC_05`).
  * **Web Portals (`SRC_06`–`SRC_10`):** AAU KVK Kokrajhar *Rabi PoP* (`SRC_06`), KVK Cachar *GKMS Bulletins* (`SRC_07`), RKB Assam *Factsheets* (`SRC_08`), DirAgri *Stats Portal* (`SRC_09`), APEDA *Assam Export Profile* (`SRC_10`).
  * **Surprise Inputs:** Unseen `.csv`, `.html`, `.pdf`, `.json`, and bilingual Assamese `.txt` files.
* **Core Responsibility:** Extracts structured agricultural records and exact provenance locators (`Page=X;Table=Y;Row=Z` or `File=...;TableRow=...`) from multi-header PDFs, HTML DOM tables, CSVs, and Assamese prose advisories.
* **Inputs & Expected Outputs:**
  * **Input:** Evaluation case dictionary (`ingest_case_dict`) or raw file path (`ingest_file`).
  * **Output:** List of raw extracted dictionaries with mandatory fields (`source_id`, `source_type`, `agent`, `locator`, `crop_name`, `variety_name`, `district_raw`, `time_period`, `metric_name`, `raw_value`, `raw_unit`, `source_text_evidence`). Raises `ValueError` on missing required fields or unparseable files (never fabricates fallback data).
* **Models & Open-Source Tools Used (with Justification):**
  * **Tools:** `pdfplumber` (header-aware PDF table grid extraction), `BeautifulSoup4` (HTML `<table>` DOM extraction), `csv.DictReader` (quoted Indian numeral CSV parsing).
  * **Model:** `Qwen/Qwen2.5-72B-Instruct` with `adapters/assam_agri_qlora_r16` (`AISemanticExtractor`) for Assamese-to-English entity transliteration (`ASSAMESE_CROP_LEXICON`) and dynamic column header mapping (`map_header_dict`).
* **Implementation Status & Known Limitations:**
  * **Status:** `done` (`M3 = 1.000`, `M5 = 1.000`, `M3_BONUS_NON_EN = 1.000`).
  * **Limitations:** Scanned image-only PDFs without embedded text layers require external OCR pre-processing before `pdfplumber` table extraction.