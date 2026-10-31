# Agent Card: `TabularPDF_Agent`

* **Assigned Sources:** SRC_01 (DES Assam Ten Major Crops), SRC_02 (ICAR-IIRR Rice Varieties), SRC_03 (ASAMB Cold Storage), SRC_04 (DirAgri Table 11(A).2), SRC_05 (IP India GI Registry)
* **Source Group:** `Document_PDF`
* **Core Responsibility:** Extracts multi-header statistical tables, cold storage capacities, and Assam-filtered variety/GI records from government PDFs.
* **Inputs & Expected Outputs:** Input: PDF file path or URL + state filter ('Assam'). Output: Validated JSON array of ExtractedFactItem with exact page/table/row locator.
* **Models & Open-Source Tools (with Justification):** Docling (TableFormer) + pdfplumber for geometric table grid extraction; Qwen/Qwen2.5-72B-Instruct (or Llama-3.3-70B) for multi-header resolution.
* **Known Limitations:** Scanned low-DPI PDFs with merged footnote symbols ('*') require routing through SelfCorrectionNode.
