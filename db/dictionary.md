# Database Data Dictionary & Validation Rules (`db/dictionary.md`)

## 1. Mandatory Provenance & Fact Columns (`M14` Completeness = 1.00)
Every row in `fact_agricultural_records` enforces `NOT NULL` and foreign-key integrity on:
* `source_id` -> references `dim_sources(source_id)`
* `extracting_agent` -> agent that produced the row (`TabularPDF_Agent`, `WebPortal_Agent`, `LiveMandi_Agent`, `GeoSpatial_Agent`)
* `run_id` -> references `extraction_runs(run_id)` with timestamp
* `source_location` -> exact page/table/row or URL/XPath locator (`Page=3;Table=1.01;Row=1`)
* `crop_id` -> references `dim_crops(crop_id)`
* `location_id` -> references `dim_locations(location_id)` (`LGD_AS_*` canonical code)
* `time_period` -> fiscal year or ISO date (`2003-04`, `2026-10-18`)
* `metric_name` -> agricultural variable (`Area`, `Production`, `Value`, `Potential_Yield`, `Modal_Mandi_Price`, `Cold_Storage_Capacity`)
* `normalized_value` & `normalized_unit` -> standardized numeric value and SI/canonical unit (`ha`, `tonnes`, `kg/ha`, `INR`, `Rs/Quintal`, `mm`, `days`, `meters`, `scale`, `pH`)

## 2. Validation Rules (`M15` Validation Pass Rate >= 0.98)
1. **Allowed Units:** `normalized_unit IN ('ha', 'tonnes', 'kg/ha', 'INR', 'Rs/Quintal', 'mm', 'days', 'meters', 'scale', 'pH')`
2. **Valid Assam LGD Codes:** `location_id LIKE 'LGD_AS_%'`
3. **Plausible Numeric Range:** `normalized_value > 0 AND normalized_value <= 1e12`

## 3. Natural Key Deduplication (`M16` Duplicate Rate = 0.00)
Enforced via `UNIQUE(source_id, source_location, crop_id, location_id, time_period, metric_name)` and `record_hash UNIQUE`.
