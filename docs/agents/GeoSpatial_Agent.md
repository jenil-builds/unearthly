# Agent Card: `GeoSpatial_Agent`

* **Assigned Sources:** SRC_12 (APART Web GIS), SRC_13 (RKB Web GIS), SRC_14 (NBSS&LUP BHOOMI Assam), SRC_15 (NESDR & ASTEC Remote Sensing)
* **Source Group:** `Geospatial_GIS`
* **Core Responsibility:** Extracts WMS layer capabilities, spatial resolution, and crop/soil theme metadata.
* **Inputs & Expected Outputs:** Input: Geoportal URL or XML/JSON capabilities file. Output: Spatial layer metadata records with resolution (m) and temporal bounds.
* **Models & Open-Source Tools (with Justification):** owslib / httpx metadata inspector + Qwen/Qwen2.5-72B-Instruct.
* **Known Limitations:** Status = partial (Metadata extraction implemented in Phase 2; full GeoTIFF pixel zonal statistics scheduled for Phase 3).
