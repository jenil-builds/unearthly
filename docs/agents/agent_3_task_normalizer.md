# Agent Card: `agent3_task` (`Agent3TaskNormalizer`)

* **Module File:** `agent3_task.py`
* **Logical Domain Roles:** `SchemaNormalizer_Agent` and `SelfCorrectionNode`.
* **Assigned Sources:** All 15 manifest sources (`SRC_01`–`SRC_15`) and all surprise inputs post-extraction.
* **Core Responsibility:** Performs deterministic post-extraction self-correction, historical/bilingual Assam district resolution to Local Government Directory (`LGD_AS_%`) codes, SI unit conversion, agronomic season inference, and natural-key SHA-256 deduplication prior to SQLite persistence.
* **Inputs & Expected Outputs:**
  * **Input:** Raw extracted dictionary from `agent2_ingestion` or `agent2b_live_gis`.
  * **Output:** Fully normalized, database-ready dictionary containing `location_id` (`LGD_AS_%`), `canonical_district`, `agro_climatic_zone`, `crop_id`, `season_category`, `normalized_value`, `normalized_unit`, `validation_status` (`VALIDATED` or `SELF_CORRECTED`), `record_hash`, `retries`, and `trajectory`.
* **Models & Open-Source Tools Used (with Justification):**
  * **`SelfCorrectionNode`:** Detects footnote asterisks (`*`), corrupt tokens (`CORRUPT_NaN_`), and formatting artifacts in `raw_value`, stripping non-numeric symbols and recording `validation_status = "SELF_CORRECTED"` and `retries = 1`.
  * **Assam LGD Dictionary (`ASSAM_LGD_MAP`):** Resolves 35+ colonial, sub-district, and Assamese Unicode district names (*Sibsagar* $\rightarrow$ `LGD_AS_300`, *Nowgong* $\rightarrow$ `LGD_AS_297`, *কামৰূপ* $\rightarrow$ `LGD_AS_291`, *যোৰহাট* $\rightarrow$ `LGD_AS_290`).
  * **Strict SI Unit Standardizer:** Converts `q/ha` $\rightarrow$ `kg/ha` ($\times 100$), `Rs. Lakh` $\rightarrow$ `INR` ($\times 10^5$), `Hectares` $\rightarrow$ `ha`, `MT`/`Tonnes` $\rightarrow$ `tonnes`, and raises `ValueError` on unsupported units (`ALLOWED_SI_UNITS`).
* **Implementation Status & Known Limitations:**
  * **Status:** `done` (`M14 = 1.000`, `M15 = 1.000`, `M16 = 0.000`, `BONUS_EVAL_1 = 1.000`, `BONUS_EVAL_2 = 1.000`).
  * **Limitations:** State-wide aggregate rows without a specific district map to `LGD_AS_00` (`Assam (State Total)`).