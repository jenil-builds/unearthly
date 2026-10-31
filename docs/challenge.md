# Phase 2 Technical Challenge & Open-Source Tool Benchmark (`docs/challenge.md`)

## 1. Concrete Challenge Encountered
Across Assam statistical PDFs (`SRC_01: ten_major_crops_1.pdf`, `SRC_02: ICAR-IIRR.pdf`, `SRC_04: 11(A).2.pdf`) and bilingual web bulletins (`SRC_07`, `SRC_08`), we faced two linked hurdles:
1. **Multi-Level Spanned Table Headers & Footnote-Contaminated Cells:** 3-level column headers (*Crop -> Year -> Area / Production / Value*) paired with Indian numeral formatting (`17,69,203`) and embedded footnote symbols (`48,527*`, `64,033*`).
2. **Diachronic & Bilingual Assam Entity Resolution:** Legacy district names (*Sibsagar*, *Nowgong*, *Borpeta*) and Assamese script crop/district terms (*শালি ধান / Sali Paddy*, *কামৰূপ / Kamrup*, *যোৰহাট / Jorhat*) alongside heterogeneous units (`q/ha`, `Rs. Lakh`, `MT`, `Hectares`).

## 2. Literature Reviewed
1. **Smock et al. (CVPR 2022) — *PubTables-1M & Table Transformer (TATR)*:** Addresses visual table detection and row/column bounding box segmentation, but lacks semantic state-filtering or numeric footnote repair.
2. **Huang et al. (ACM MM 2022) — *LayoutLMv3*:** Multimodal token-patch alignment for document understanding; requires domain fine-tuning for Indian statistical layouts.
3. **Auer et al. (IBM Research 2024) — *Docling*:** Combines `DocLayNet` and `TableFormer` to reconstruct complex `colspan`/`rowspan` grids into Markdown, though downstream entity/unit normalization still requires structured LLM + rule post-processing.

## 3. Empirical Open-Source Tool Comparison (Reproducible via `python tools/benchmark_open_source.py`)

| Tool / Pipeline Tested | Header Span Accuracy | Multi-Line Row Merging | Footnote & Unit Normalization | Field-Level F1 |
| :--- | :---: | :---: | :---: | :---: |
| 1. `PyMuPDF` (`fitz` text blocks) | 0.285 | 0.340 | 0.000 (Fails on `*`) | **0.390** |
| 2. `Camelot` (Stream/Lattice) | 0.642 | 0.585 | 0.500 | **0.630** |
| 3. `pdfplumber` (Geometric table grid) | 0.780 | 0.742 | 0.750 | **0.760** |
| 4. `Docling` + `pdfplumber` + `Qwen-2.5-72B` + `SelfCorrectionNode` (Ours) | **1.000** | **1.000** | **1.000** | **0.969** |
