# Agent Card: `SchemaNormalizer_Agent`

* **Assigned Sources:** All 15 sources (Post-extraction normalization & validation gate)
* **Source Group:** `All_Groups`
* **Core Responsibility:** Resolves historical/Assamese district names (Sibsagar->Sivasagar, Nowgong->Nagaon, কামৰূপ->Kamrup) to LGD codes, converts units to SI, strips footnotes via SelfCorrectionNode, and commits idempotent rows to SQLite.
* **Inputs & Expected Outputs:** Input: Raw AgentExtractionPayload. Output: Validated relational database rows in fact_agricultural_records.
* **Models & Open-Source Tools (with Justification):** Deterministic Python LGD dictionary + SI unit converter + SHA-256 natural key deduplicator.
* **Known Limitations:** Unseen village-level toponyms without district context map to state-level LGD_AS_00.
