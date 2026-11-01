# Agent Card: `agent2b_live_gis` (`Agent2BLiveGIS`)

* **Module File:** `agent2b_live_gis.py`
* **Logical Domain Roles:** Consolidates `LiveMandi_Agent` (`Database_Dashboard`) and `GeoSpatial_Agent` (`Geospatial_GIS`).
* **Assigned Sources:**
  * **Live Market Dashboard (`SRC_11`):** AMIU (AAU Jorhat) Live Market Intelligence Dashboard (`amiu.aau.ac.in`).
  * **Geospatial Portals (`SRC_12`–`SRC_15`):** AAU-IRRI APART Web-GIS (`SRC_12`), RKB Assam Web-GIS (`SRC_13`), NBSS&LUP BHOOMI Assam Soil Geoportal (`SRC_14`), NESDR & ASTEC Remote Sensing Catalog (`SRC_15`).
* **Core Responsibility:** Offloads dynamic market price scraping (`Modal_Mandi_Price` in `Rs/Quintal`) and Web-GIS layer metadata extraction (`Spatial_Resolution_Meters`, `Mapped_Rice_Area`, `Map_Scale_Denominator`, `Mean_Topsoil_pH`) into an isolated worker module.
* **Inputs & Expected Outputs:**
  * **Input:** Structured dashboard or WMS layer case dictionary (`ingest_case_dict`).
  * **Output:** Validated raw record list stamped with `agent = "agent2b_live_gis"` and exact `URL=...;Row=...` or `WMS=...;Layer=...` provenance locators. Enforces strict key validation (`REQUIRED_KEYS`) so incomplete inputs raise `ValueError` rather than fabricating defaults.
* **Models & Open-Source Tools Used (with Justification):**
  * **Tools:** DOM table scraper (`scrape_amiu_mandi_tool`) and WMS/Geoportal metadata inspector (`owslib` / `httpx` capabilities parser).
  * **Model:** `Qwen/Qwen2.5-72B-Instruct` for normalizing spatial layer descriptors into structured schema metrics.
* **Implementation Status & Known Limitations:**
  * **Status:** `done` for `SRC_11` (live mandi prices); `partial` for `SRC_12`–`SRC_15` (WMS layer metadata and published area summaries extracted in Phase 2; full GeoTIFF raster pixel zonal statistics scheduled for Phase 3).