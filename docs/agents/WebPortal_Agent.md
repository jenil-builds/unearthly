# Agent Card: `WebPortal_Agent`

* **Assigned Sources:** SRC_06 (AAU Rabi PoP 2023), SRC_07 (KVK Cachar GKMS Bulletins), SRC_08 (RKB Assam Factsheets), SRC_09 (DirAgri Stats Portal), SRC_10 (APEDA Assam)
* **Source Group:** `Web_Portal`
* **Core Responsibility:** Scrapes semi-structured HTML tables, bilingual Assamese/English agromet advisories, and agronomic Package of Practices parameters.
* **Inputs & Expected Outputs:** Input: Portal URL or local HTML/TXT file. Output: Structured agronomic records (variety, sowing window, yield in q/ha or kg/ha, rainfall thresholds).
* **Models & Open-Source Tools (with Justification):** httpx (with custom NIC SSL bypass) + BeautifulSoup4 + trafilatura; Qwen/Qwen2.5-72B-Instruct for bilingual English/Assamese entity extraction.
* **Known Limitations:** Potential agronomic yields (PoP) represent recommended ceilings rather than empirical district harvest.
