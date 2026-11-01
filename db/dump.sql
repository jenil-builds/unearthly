BEGIN TRANSACTION;
CREATE TABLE dim_crops (
    crop_id TEXT PRIMARY KEY,
    crop_name TEXT NOT NULL,
    variety_name TEXT NOT NULL DEFAULT 'General',
    season_category TEXT NOT NULL
);
INSERT INTO "dim_crops" VALUES('a12b397c6524','Rice (Paddy)','Autumn Paddy (Ahu)','Autumn (Ahu)');
INSERT INTO "dim_crops" VALUES('2a0f2be01a25','Rice (Paddy)','Summer Paddy (Boro)','Rabi / Summer');
INSERT INTO "dim_crops" VALUES('078c7e0515c1','Rapeseed & Mustard','General','Rabi / Summer');
INSERT INTO "dim_crops" VALUES('ff24d303e952','Blackgram (Matikalai)','General','Rabi / Summer');
INSERT INTO "dim_crops" VALUES('06e88ba5bc2e','Rice (Paddy)','DRR Dhan 42','Annual / Multi-Season');
INSERT INTO "dim_crops" VALUES('6e983f677c10','Cold Storage','ASAMB Kharupetia','Annual / Multi-Season');
INSERT INTO "dim_crops" VALUES('16faa1e6bab1','Jute','Capsularis','Annual / Multi-Season');
INSERT INTO "dim_crops" VALUES('6819af5baaf2','Wheat','DBW-14','Rabi / Summer');
INSERT INTO "dim_crops" VALUES('923833f44626','Wheat','Sonalika','Rabi / Summer');
INSERT INTO "dim_crops" VALUES('b06f00f1ccd2','Grass Pea (Khesari)','Ratan (Bio L-212)','Annual / Multi-Season');
INSERT INTO "dim_crops" VALUES('fb6d36873543','Rice (Paddy)','শালি ধান (Sali Rice)','Kharif (Winter/Sali)');
INSERT INTO "dim_crops" VALUES('d167ea5b350e','Rapeseed & Mustard','সৰিয়হ (Mustard)','Rabi / Summer');
INSERT INTO "dim_crops" VALUES('2c547e48d931','Rice (Paddy)','Kanaklata (Boro)','Rabi / Summer');
INSERT INTO "dim_crops" VALUES('b5ad7cd0ec4b','Potato','Kufri Jyoti','Rabi / Summer');
INSERT INTO "dim_crops" VALUES('b7e3f3536fea','Bhut Jolokia (King Chilli)','Assam Export Cluster','Annual / Multi-Season');
INSERT INTO "dim_crops" VALUES('24acfeee6458','Potato','Local Red','Rabi / Summer');
INSERT INTO "dim_crops" VALUES('66ade8bf9885','Tomato','Hybrid','Annual / Multi-Season');
INSERT INTO "dim_crops" VALUES('669dc4bf6396','Rice (Paddy)','জহা চাউল (Joha Rice)','Annual / Multi-Season');
INSERT INTO "dim_crops" VALUES('5c18d480bfc1','Onion','Nasik Red','Annual / Multi-Season');
INSERT INTO "dim_crops" VALUES('e5d8498f30b4','Cabbage','Winter Fresh','Annual / Multi-Season');
INSERT INTO "dim_crops" VALUES('b4cf0f079e4a','Green Chilli','Local Hot','Annual / Multi-Season');
INSERT INTO "dim_crops" VALUES('8462f45d3863','Rice-Fallow Spatial Layer','Sentinel-1/2 SAR+Optical','Annual / Multi-Season');
INSERT INTO "dim_crops" VALUES('b106bf8f5c84','Rice (Paddy)','Kharif Satellite Mask','Kharif (Winter/Sali)');
INSERT INTO "dim_crops" VALUES('69865f2512e0','Rice (Paddy)','Flood-Prone Agro-Zone','Annual / Multi-Season');
INSERT INTO "dim_crops" VALUES('682b1b09071c','Soil Resource Layer','Alluvial Acidic Soil','Annual / Multi-Season');
INSERT INTO "dim_crops" VALUES('0088fb21f5c9','Land Use Land Cover','Assam Agri Cropland Mask','Annual / Multi-Season');
INSERT INTO "dim_crops" VALUES('e1bfe9d5fee8','Rice (Paddy)','Boro Satellite Mask','Rabi / Summer');
INSERT INTO "dim_crops" VALUES('23f0bb24f0f4','Rice (Paddy)','Winter Paddy (Sali)','Kharif (Winter/Sali)');
INSERT INTO "dim_crops" VALUES('47e8938bc4db','Rapeseed & Mustard','TS-38','Rabi / Summer');
INSERT INTO "dim_crops" VALUES('09556c6dee01','Wheat','DBW-187','Rabi / Summer');
INSERT INTO "dim_crops" VALUES('b3a7a8ff9e4e','Potato','Kufri Pukhraj','Rabi / Summer');
INSERT INTO "dim_crops" VALUES('48e5e0708071','Rice (Paddy)','ৰঞ্জিত চাব-১ (Ranjit Sub-1)','Kharif (Winter/Sali)');
INSERT INTO "dim_crops" VALUES('2018dedce162','Rapeseed & Mustard','TS-46','Rabi / Summer');
CREATE TABLE dim_locations (
    location_id TEXT PRIMARY KEY CHECK (location_id LIKE 'LGD_AS_%'),
    canonical_district_name TEXT NOT NULL,
    agro_climatic_zone TEXT NOT NULL,
    state_name TEXT NOT NULL DEFAULT 'Assam'
);
INSERT INTO "dim_locations" VALUES('LGD_AS_294','Kokrajhar','Lower Brahmaputra Valley Zone','Assam');
INSERT INTO "dim_locations" VALUES('LGD_AS_282','Cachar','Barak Valley Zone','Assam');
INSERT INTO "dim_locations" VALUES('LGD_AS_301','Sonitpur','North Bank Plains Zone','Assam');
INSERT INTO "dim_locations" VALUES('LGD_AS_288','Golaghat','Upper Brahmaputra Valley Zone','Assam');
INSERT INTO "dim_locations" VALUES('LGD_AS_283','Darrang','North Bank Plains Zone','Assam');
INSERT INTO "dim_locations" VALUES('LGD_AS_00','Assam (State Total)','All Zones','Assam');
INSERT INTO "dim_locations" VALUES('LGD_AS_300','Sivasagar','Upper Brahmaputra Valley Zone','Assam');
INSERT INTO "dim_locations" VALUES('LGD_AS_297','Nagaon','Central Brahmaputra Valley Zone','Assam');
INSERT INTO "dim_locations" VALUES('LGD_AS_280','Barpeta','Lower Brahmaputra Valley Zone','Assam');
INSERT INTO "dim_locations" VALUES('LGD_AS_290','Jorhat','Upper Brahmaputra Valley Zone','Assam');
INSERT INTO "dim_locations" VALUES('LGD_AS_291','Kamrup','Lower Brahmaputra Valley Zone','Assam');
CREATE TABLE dim_sources (
    source_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    url TEXT NOT NULL,
    source_group TEXT NOT NULL,
    temporal_coverage TEXT NOT NULL,
    assigned_agent TEXT NOT NULL CHECK (assigned_agent IN ('agent2_ingestion', 'agent2b_live_gis')),
    implementation_status TEXT NOT NULL CHECK (implementation_status IN ('done', 'partial', 'pending')),
    known_limitations TEXT
);
INSERT INTO "dim_sources" VALUES('SRC_01','DES Assam - Ten Major Crops in Assam','https://des.assam.gov.in/sites/default/files/swf_utility_folder/departments/ecostat_medhassu_in_oid_3/menu/document/ten_major_crops_1.pdf','Document_PDF','2003-04 to 2012-13','agent2_ingestion','done','Series ends 2012-13; multi-row headers and footnote markers');
INSERT INTO "dim_sources" VALUES('SRC_02','ICAR-IIRR - Released Rice Varieties and Hybrids','https://www.icar-iirr.org/3.ICAR-IIRR_Varietiesandhybrids_Available_for_Commercialization_through_Licensing.pdf','Document_PDF','1997-2013','agent2_ingestion','done','National table; requires Assam agro-climatic filtering');
INSERT INTO "dim_sources" VALUES('SRC_03','ASAMB - Cold Storage Facilities List','https://asamb.assam.gov.in/sites/default/files/swf_utility_folder/departments/asamb_medhassu_in_oid_7/menu/information_and_services/cold_storage_under_asamb.pdf','Document_PDF','Current','agent2_ingestion','done','Covers 18000 MT public ASAMB units only');
INSERT INTO "dim_sources" VALUES('SRC_04','DirAgri Assam - Statistical Table 11(A).2','https://diragri.assam.gov.in/sites/default/files/swf_utility_folder/departments/diragri_medhassu_in_oid_4/portlet/level_2/11%28A%29.2.pdf','Document_PDF','2022-23','agent2_ingestion','done','Contains footnote symbols in numeric columns');
INSERT INTO "dim_sources" VALUES('SRC_05','IP India - State-wise Registered GI of India','https://ipindia.gov.in/frontend/pdf/gi/registered/State_wise_Registered_GI_of_India.pdf','Document_PDF','Current','agent2_ingestion','done','National registry; filtered for Assam Agri GIs');
INSERT INTO "dim_sources" VALUES('SRC_06','AAU - Package of Practices for Rabi Crops 2023','https://kvkkokrajhar.aau.ac.in/pop.php','Web_Portal','2023','agent2_ingestion','done','Rabi season potential yields only');
INSERT INTO "dim_sources" VALUES('SRC_07','KVK Cachar - GKMS Agromet Advisory Bulletins','https://kvkcachar.aau.ac.in/agro.html','Web_Portal','2025-26','agent2_ingestion','done','Bilingual Assamese/English Barak Valley advisories');
INSERT INTO "dim_sources" VALUES('SRC_08','RKB Assam - Rice Knowledge Bank Factsheets','https://rkbassam.aau.ac.in/factsheets','Web_Portal','Current','agent2_ingestion','done','Semi-structured agronomic factsheets');
INSERT INTO "dim_sources" VALUES('SRC_09','DirAgri Assam - Agricultural Statistics Portal','https://diragri.assam.gov.in/information-services/agricultural-statistics','Web_Portal','2023-24','agent2_ingestion','done','NIC SSL intermediate certificate chain issues');
INSERT INTO "dim_sources" VALUES('SRC_10','APEDA - Assam Agri Export State Profile','https://apeda.gov.in/Assam','Web_Portal','2024-25','agent2_ingestion','done','State-level export cluster metrics');
INSERT INTO "dim_sources" VALUES('SRC_11','AMIU (AAU Jorhat) - Live Market Dashboard','https://amiu.aau.ac.in/','Database_Dashboard','2023-2026','agent2b_live_gis','done','Live rolling ticker; no bulk historical archive');
INSERT INTO "dim_sources" VALUES('SRC_12','AAU-IRRI APART Web GIS - Rice-Fallow Mapping','https://apartgis.aau.ac.in/','Geospatial_GIS','2017-2025','agent2b_live_gis','partial','Metadata extracted; raw GeoTIFF raster parsing in Phase 3');
INSERT INTO "dim_sources" VALUES('SRC_13','RKB Assam - Web GIS Portal','https://rkbassam.aau.ac.in/web-gis','Geospatial_GIS','Current','agent2b_live_gis','partial','WMS capabilities extracted; raster stats in Phase 3');
INSERT INTO "dim_sources" VALUES('SRC_14','NBSS&LUP BHOOMI Geoportal - Assam Soil','https://bhoomigeoportal-nbsslup.in/BHOOMI_StateWise/Assam.php','Geospatial_GIS','Current','agent2b_live_gis','partial','Metadata extracted; spatial polygon query in Phase 3');
INSERT INTO "dim_sources" VALUES('SRC_15','NESDR & ASTEC Remote Sensing Datasets','https://www.nesdr.gov.in/search/og_group_ref/148/type/dataset?sort_by=changed','Geospatial_GIS','Multi-year','agent2b_live_gis','partial','Catalog metadata extracted; raster tiling in Phase 3');
INSERT INTO "dim_sources" VALUES('SURPRISE_01','Live Surprise Input (SURPRISE_01)','local://Page=1','Document_PDF','2024-25','agent2_ingestion','done','Live surprise input evaluated via agent1->agent2->agent3');
INSERT INTO "dim_sources" VALUES('SURPRISE_HTML','Live Surprise Input (SURPRISE_HTML)','local://File=surprise_2_aau_bulletin.html','Web_Portal','2025','agent2_ingestion','done','Live surprise input evaluated via agent1->agent2->agent3');
INSERT INTO "dim_sources" VALUES('SURPRISE_AS_TXT','Live Surprise Input (SURPRISE_AS_TXT)','local://File=surprise_3_assamese_advisory.txt','Web_Portal','2025-26','agent2_ingestion','done','Live surprise input evaluated via agent1->agent2->agent3');
CREATE TABLE extraction_runs (
    run_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    agent_name TEXT NOT NULL CHECK (agent_name IN ('agent2_ingestion', 'agent2b_live_gis')),
    llm_model_id TEXT NOT NULL,
    started_at_utc TEXT NOT NULL,
    completed_at_utc TEXT NOT NULL,
    latency_ms REAL NOT NULL,
    tokens_used INTEGER NOT NULL,
    retry_count INTEGER NOT NULL DEFAULT 0,
    manual_interventions INTEGER NOT NULL DEFAULT 0,
    run_status TEXT NOT NULL CHECK (run_status IN ('COMPLETED', 'PARTIAL', 'FAILED')),
    error_message TEXT,
    FOREIGN KEY (source_id) REFERENCES dim_sources(source_id)
);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_01_51f31b2f','SRC_01','agent2_ingestion','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.68,420,0,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_01_f3528210','SRC_01','agent2_ingestion','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.52,420,0,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_01_16e93fa8','SRC_01','agent2_ingestion','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.52,420,0,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_01_8473928b','SRC_01','agent2_ingestion','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.52,420,0,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_01_6a1e1581','SRC_01','agent2_ingestion','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_01_3c80e3f3','SRC_01','agent2_ingestion','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_01_c65d6698','SRC_01','agent2_ingestion','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,1,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_02_073cadbf','SRC_02','agent2_ingestion','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_03_3cd09c40','SRC_03','agent2_ingestion','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_04_2e5d81bc','SRC_04','agent2_ingestion','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,1,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_06_12d01d97','SRC_06','agent2_ingestion','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_06_c7df41fb','SRC_06','agent2_ingestion','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_06_f0e67d97','SRC_06','agent2_ingestion','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_06_92112fa4','SRC_06','agent2_ingestion','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_07_5215d7a4','SRC_07','agent2_ingestion','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_07_7f3aec25','SRC_07','agent2_ingestion','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_08_a0f75e73','SRC_08','agent2_ingestion','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_08_2915aeaf','SRC_08','agent2_ingestion','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_09_f3bcf877','SRC_09','agent2_ingestion','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_10_7b591936','SRC_10','agent2_ingestion','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_11_29706285','SRC_11','agent2b_live_gis','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_11_c2289165','SRC_11','agent2b_live_gis','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_11_56df175c','SRC_11','agent2b_live_gis','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_11_6a936473','SRC_11','agent2b_live_gis','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_11_0a1863b5','SRC_11','agent2b_live_gis','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_11_671b5c77','SRC_11','agent2b_live_gis','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_12_91928b31','SRC_12','agent2b_live_gis','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,1,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_12_ed4785a0','SRC_12','agent2b_live_gis','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,1,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_13_d5270185','SRC_13','agent2b_live_gis','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,1,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_14_d76ccdd6','SRC_14','agent2b_live_gis','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,1,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_15_2cc9a2e6','SRC_15','agent2b_live_gis','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,1,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SRC_15_9e21e352','SRC_15','agent2b_live_gis','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,1,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SURPRISE_01_20ce7df7','SURPRISE_01','agent2_ingestion','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.52,420,1,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SURPRISE_01_77dd0829','SURPRISE_01','agent2_ingestion','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SURPRISE_HTML_ff0fd20a','SURPRISE_HTML','agent2_ingestion','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SURPRISE_HTML_16efffa6','SURPRISE_HTML','agent2_ingestion','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SURPRISE_AS_TXT_2f6d0977','SURPRISE_AS_TXT','agent2_ingestion','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,0,0,'COMPLETED',NULL);
INSERT INTO "extraction_runs" VALUES('RUN_SURPRISE_AS_TXT_32a5bfa5','SURPRISE_AS_TXT','agent2_ingestion','Qwen/Qwen2.5-72B-Instruct','2026-11-01T08:57:35.775012+00:00','2026-11-01T08:57:35.775012+00:00',112.51,420,1,0,'COMPLETED',NULL);
CREATE TABLE fact_agricultural_records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_hash TEXT NOT NULL UNIQUE,
    source_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    run_id TEXT NOT NULL,
    extracting_agent TEXT NOT NULL CHECK (extracting_agent IN ('agent2_ingestion', 'agent2b_live_gis')),
    source_location TEXT NOT NULL,
    location_id TEXT NOT NULL,
    crop_id TEXT NOT NULL,
    time_period TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    raw_value_text TEXT NOT NULL,
    raw_unit TEXT NOT NULL,
    normalized_value REAL NOT NULL CHECK (normalized_value > 0 AND normalized_value <= 1e12),
    normalized_unit TEXT NOT NULL CHECK (normalized_unit IN ('ha', 'tonnes', 'kg/ha', 'INR', 'Rs/Quintal', 'mm', 'days', 'meters', 'scale', 'pH')),
    validation_status TEXT NOT NULL CHECK (validation_status IN ('VALIDATED', 'SELF_CORRECTED')),
    FOREIGN KEY (source_id) REFERENCES dim_sources(source_id),
    FOREIGN KEY (run_id) REFERENCES extraction_runs(run_id),
    FOREIGN KEY (location_id) REFERENCES dim_locations(location_id),
    FOREIGN KEY (crop_id) REFERENCES dim_crops(crop_id),
    UNIQUE (
        source_id,
        source_location,
        crop_id,
        location_id,
        time_period,
        metric_name
    )
);
INSERT INTO "fact_agricultural_records" VALUES(1,'51f31b2f1a09ac8f51c9c927','SRC_01','Document_PDF','RUN_SRC_01_51f31b2f','agent2_ingestion','Page=3;Table=1.01;Row=1','LGD_AS_00','23f0bb24f0f4','2003-04','Area','17,69,203','Hectares',1769203.0,'ha','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(2,'f3528210aa61341b434e6196','SRC_01','Document_PDF','RUN_SRC_01_f3528210','agent2_ingestion','Page=3;Table=1.01;Row=1','LGD_AS_00','23f0bb24f0f4','2003-04','Production','44,26,729','Tonnes',4426729.0,'tonnes','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(3,'16e93fa8bf2076ed14f6fc65','SRC_01','Document_PDF','RUN_SRC_01_16e93fa8','agent2_ingestion','Page=3;Table=1.01;Row=1','LGD_AS_00','23f0bb24f0f4','2003-04','Value','2,32,806','Rs. Lakh',23280600000.0,'INR','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(4,'8473928bf9a5f8e28db07557','SRC_01','Document_PDF','RUN_SRC_01_8473928b','agent2_ingestion','Page=3;Table=1.01;Row=2','LGD_AS_00','a12b397c6524','2003-04','Area','4,41,142','Hectares',441142.0,'ha','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(5,'6a1e1581a3d628ea2dc62c4b','SRC_01','Document_PDF','RUN_SRC_01_6a1e1581','agent2_ingestion','Page=3;Table=1.01;Row=3','LGD_AS_00','2a0f2be01a25','2003-04','Area','3,19,480','Hectares',319480.0,'ha','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(6,'3c80e3f369e87f9503ce8900','SRC_01','Document_PDF','RUN_SRC_01_3c80e3f3','agent2_ingestion','Page=4;Table=1.04;Row=10','LGD_AS_00','078c7e0515c1','2012-13','Area','2,79,496','Hectares',279496.0,'ha','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(7,'c65d6698ba22231f125627fa','SRC_01','Document_PDF','RUN_SRC_01_c65d6698','agent2_ingestion','Page=4;Table=1.08;Row=10','LGD_AS_300','ff24d303e952','2012-13','Area','48,527*','Hectares',48527.0,'ha','SELF_CORRECTED');
INSERT INTO "fact_agricultural_records" VALUES(8,'073cadbf47de13a78afe138b','SRC_02','Document_PDF','RUN_SRC_02_073cadbf','agent2_ingestion','Page=2;Table=1;Row=14','LGD_AS_00','06e88ba5bc2e','2014','Potential_Yield','52.0','q/ha',5200.0,'kg/ha','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(9,'3cd09c40fc377d16290130e5','SRC_03','Document_PDF','RUN_SRC_03_3cd09c40','agent2_ingestion','Page=1;Table=1;Row=1','LGD_AS_283','6e983f677c10','Current','Cold_Storage_Capacity','5,000','MT',5000.0,'tonnes','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(10,'2e5d81bc490c22784f3737db','SRC_04','Document_PDF','RUN_SRC_04_2e5d81bc','agent2_ingestion','Page=1;Table=11(A).2;Row=4','LGD_AS_297','16faa1e6bab1','2022-23','Area','64,033*','Hectares',64033.0,'ha','SELF_CORRECTED');
INSERT INTO "fact_agricultural_records" VALUES(11,'12d01d970cebf880e8d03084','SRC_06','Web_Portal','RUN_SRC_06_12d01d97','agent2_ingestion','URL=kvkkokrajhar.aau.ac.in/pop.php;Table=Wheat_1','LGD_AS_291','6819af5baaf2','2023','Recommended_Yield_Irrigated','32.5','q/ha',3250.0,'kg/ha','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(12,'c7df41fb6ef2630331c3d6cf','SRC_06','Web_Portal','RUN_SRC_06_c7df41fb','agent2_ingestion','URL=kvkkokrajhar.aau.ac.in/pop.php;Table=Wheat_2','LGD_AS_280','923833f44626','2023','Recommended_Yield_Rainfed','19.0','q/ha',1900.0,'kg/ha','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(13,'f0e67d97c30fb3bb8e027bf6','SRC_06','Web_Portal','RUN_SRC_06_f0e67d97','agent2_ingestion','URL=kvkkokrajhar.aau.ac.in/pop.php;Table=Pulses_1','LGD_AS_297','b06f00f1ccd2','2023','Recommended_Yield_Rainfed','11.0','q/ha',1100.0,'kg/ha','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(14,'92112fa47f4c1e2009694810','SRC_06','Web_Portal','RUN_SRC_06_92112fa4','agent2_ingestion','URL=kvkkokrajhar.aau.ac.in/pop.php;Table=Mustard_1','LGD_AS_294','47e8938bc4db','2023','Recommended_Yield_Rainfed','12.5','q/ha',1250.0,'kg/ha','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(15,'5215d7a4fab71c7ed761b446','SRC_07','Web_Portal','RUN_SRC_07_5215d7a4','agent2_ingestion','URL=kvkcachar.aau.ac.in/agro.html;Section=GKMS_As_1','LGD_AS_282','fb6d36873543','2025-26','GKMS_Rainfall_Advisory_Threshold','45.0','mm',45.0,'mm','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(16,'7f3aec2526fe0ad2db6b458f','SRC_07','Web_Portal','RUN_SRC_07_7f3aec25','agent2_ingestion','URL=kvkcachar.aau.ac.in/agro.html;Section=GKMS_As_2','LGD_AS_282','d167ea5b350e','2025-26','Seed_Rate_Recommendation','10.0','kg/ha',10.0,'kg/ha','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(17,'a0f75e737cc7a75b2aed3455','SRC_08','Web_Portal','RUN_SRC_08_a0f75e73','agent2_ingestion','URL=rkbassam.aau.ac.in/factsheets;Section=Sub1','LGD_AS_290','48e5e0708071','2024','Submergence_Tolerance_Days','14','days',14.0,'days','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(18,'2915aeafa83dcec064dce43e','SRC_08','Web_Portal','RUN_SRC_08_2915aeaf','agent2_ingestion','URL=rkbassam.aau.ac.in/factsheets;Section=Boro','LGD_AS_290','2c547e48d931','2024','Potential_Yield','55.0','q/ha',5500.0,'kg/ha','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(19,'f3bcf877125bbcd26a46ba26','SRC_09','Web_Portal','RUN_SRC_09_f3bcf877','agent2_ingestion','URL=diragri.assam.gov.in;Table=Hort_Potato','LGD_AS_301','b5ad7cd0ec4b','2023-24','Area','77,894','Hectares',77894.0,'ha','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(20,'7b59193669c1cefa699bafaf','SRC_10','Web_Portal','RUN_SRC_10_7b591936','agent2_ingestion','URL=apeda.gov.in/Assam;Section=ExportCluster','LGD_AS_288','b7e3f3536fea','2024-25','Export_Shipment_Volume','120.0','MT',120.0,'tonnes','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(21,'29706285b906300b0062c3a6','SRC_11','Database_Dashboard','RUN_SRC_11_29706285','agent2b_live_gis','URL=amiu.aau.ac.in;Row=1','LGD_AS_290','24acfeee6458','2026-10-18','Modal_Mandi_Price','2,450','Rs/Quintal',2450.0,'Rs/Quintal','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(22,'c228916520ebd7b1fb4ad8aa','SRC_11','Database_Dashboard','RUN_SRC_11_c2289165','agent2b_live_gis','URL=amiu.aau.ac.in;Row=2','LGD_AS_291','66ade8bf9885','2026-10-18','Modal_Mandi_Price','3,100','Rs/Quintal',3100.0,'Rs/Quintal','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(23,'56df175c14491e8587ac8d34','SRC_11','Database_Dashboard','RUN_SRC_11_56df175c','agent2b_live_gis','URL=amiu.aau.ac.in;Row=3','LGD_AS_290','669dc4bf6396','2026-10-18','Modal_Mandi_Price','6,800','Rs/Quintal',6800.0,'Rs/Quintal','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(24,'6a936473351b925b92b17e89','SRC_11','Database_Dashboard','RUN_SRC_11_6a936473','agent2b_live_gis','URL=amiu.aau.ac.in;Row=4','LGD_AS_297','5c18d480bfc1','2026-10-18','Modal_Mandi_Price','3,600','Rs/Quintal',3600.0,'Rs/Quintal','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(25,'0a1863b515836d1c781c08bc','SRC_11','Database_Dashboard','RUN_SRC_11_0a1863b5','agent2b_live_gis','URL=amiu.aau.ac.in;Row=5','LGD_AS_283','e5d8498f30b4','2026-10-18','Modal_Mandi_Price','1,850','Rs/Quintal',1850.0,'Rs/Quintal','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(26,'671b5c771c4ec19f92702e93','SRC_11','Database_Dashboard','RUN_SRC_11_671b5c77','agent2b_live_gis','URL=amiu.aau.ac.in;Row=6','LGD_AS_280','b4cf0f079e4a','2026-10-18','Modal_Mandi_Price','4,200','Rs/Quintal',4200.0,'Rs/Quintal','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(27,'91928b310ffb8f846b2adb58','SRC_12','Geospatial_GIS','RUN_SRC_12_91928b31','agent2b_live_gis','WMS=apartgis.aau.ac.in;Layer=RiceFallow_2024','LGD_AS_00','8462f45d3863','2024-25','Spatial_Resolution_Meters','10.0','meters',10.0,'meters','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(28,'ed4785a0e2f9dd1a4c6a47ae','SRC_12','Geospatial_GIS','RUN_SRC_12_ed4785a0','agent2b_live_gis','WMS=apartgis.aau.ac.in;Layer=KharifRice_Area','LGD_AS_00','b106bf8f5c84','2023-24','Mapped_Rice_Area','18,45,000','Hectares',1845000.0,'ha','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(29,'d5270185ef7af1b90c89ef69','SRC_13','Geospatial_GIS','RUN_SRC_13_d5270185','agent2b_live_gis','WMS=rkbassam.aau.ac.in/web-gis;Layer=FloodProne','LGD_AS_290','69865f2512e0','2024','Map_Scale_Denominator','50000','scale',50000.0,'scale','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(30,'d76ccdd67792c1d22d404f09','SRC_14','Geospatial_GIS','RUN_SRC_14_d76ccdd6','agent2b_live_gis','WMS=bhoomigeoportal-nbsslup.in;Layer=Soil_pH','LGD_AS_291','682b1b09071c','2023','Mean_Topsoil_pH','5.4','pH',5.4,'pH','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(31,'2cc9a2e648f2a7d8bda481a1','SRC_15','Geospatial_GIS','RUN_SRC_15_2cc9a2e6','agent2b_live_gis','WMS=nesdr.gov.in;Dataset=148_LULC','LGD_AS_00','0088fb21f5c9','2022-23','Spatial_Resolution_Meters','24.0','meters',24.0,'meters','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(32,'9e21e352a965a006f540a16e','SRC_15','Geospatial_GIS','RUN_SRC_15_9e21e352','agent2b_live_gis','WMS=astec.assam.gov.in;Layer=BoroRice_CropMask','LGD_AS_297','e1bfe9d5fee8','2023-24','Mapped_Rice_Area','68,400','Hectares',68400.0,'ha','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(33,'20ce7df70f65ce7f23210065','SURPRISE_01','Document_PDF','RUN_SURPRISE_01_20ce7df7','agent2_ingestion','Page=1;Table=S1;Row=1','LGD_AS_300','23f0bb24f0f4','2024-25','Area','114,200*','Hectares',114200.0,'ha','SELF_CORRECTED');
INSERT INTO "fact_agricultural_records" VALUES(34,'77dd08293721c3bd5072f099','SURPRISE_01','Document_PDF','RUN_SURPRISE_01_77dd0829','agent2_ingestion','Page=1;Table=S1;Row=2','LGD_AS_297','47e8938bc4db','2024-25','Production','42,800','Tonnes',42800.0,'tonnes','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(35,'ff0fd20ab243a1fe5dbe4b97','SURPRISE_HTML','Web_Portal','RUN_SURPRISE_HTML_ff0fd20a','agent2_ingestion','File=surprise_2_aau_bulletin.html;TableRow=1','LGD_AS_291','09556c6dee01','2025','Recommended_Yield_Irrigated','34.0','q/ha',3400.0,'kg/ha','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(36,'16efffa6bb8766a08265a6e5','SURPRISE_HTML','Web_Portal','RUN_SURPRISE_HTML_16efffa6','agent2_ingestion','File=surprise_2_aau_bulletin.html;TableRow=2','LGD_AS_280','b3a7a8ff9e4e','2025','Modal_Mandi_Price','2,350','Rs/Quintal',2350.0,'Rs/Quintal','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(37,'2f6d0977df415acba828fbb5','SURPRISE_AS_TXT','Web_Portal','RUN_SURPRISE_AS_TXT_2f6d0977','agent2_ingestion','File=surprise_3_assamese_advisory.txt;Line=2','LGD_AS_290','48e5e0708071','2025-26','Potential_Yield','54.5','q/ha',5450.0,'kg/ha','VALIDATED');
INSERT INTO "fact_agricultural_records" VALUES(38,'32a5bfa522a36f15cf221fac','SURPRISE_AS_TXT','Web_Portal','RUN_SURPRISE_AS_TXT_32a5bfa5','agent2_ingestion','File=surprise_3_assamese_advisory.txt;Line=3','LGD_AS_291','2018dedce162','2025-26','Area','18,450*','Hectares',18450.0,'ha','SELF_CORRECTED');
CREATE INDEX idx_fact_source ON fact_agricultural_records(source_id);
CREATE INDEX idx_fact_agent ON fact_agricultural_records(extracting_agent);
CREATE INDEX idx_fact_location ON fact_agricultural_records(location_id);
CREATE INDEX idx_fact_crop ON fact_agricultural_records(crop_id);
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('fact_agricultural_records',38);
COMMIT;
