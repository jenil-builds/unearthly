# Agent Card: `LiveMandi_Agent`

* **Assigned Sources:** SRC_11 (AMIU AAU Jorhat Live Market Intelligence Dashboard)
* **Source Group:** `Database_Dashboard`
* **Core Responsibility:** Captures rolling daily commodity arrivals and modal mandi prices across Assam markets.
* **Inputs & Expected Outputs:** Input: Dashboard URL or CSV/HTML snapshot. Output: Standardized MandiPrice records (INR/quintal, market LGD code, date).
* **Models & Open-Source Tools (with Justification):** Playwright / BeautifulSoup4 DOM table parser + deterministic unit normalizer.
* **Known Limitations:** Live dashboard provides rolling snapshots without bulk multi-year historical archive download.
