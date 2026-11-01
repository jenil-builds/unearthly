"""
Reproducible Open-Source Tool Benchmark for Section 2 (docs/challenge.md)
Run: python tools/benchmark_open_source.py
"""

import re
from typing import List, Tuple, Set
from agent2_ingestion import AISemanticExtractor
from agent3_task import Agent3TaskNormalizer

SAMPLE_TABLE_TEXT = """
Crop: Winter Paddy | 2003-04 | District: Assam (State Total) | Area: 17,69,203 Hectares | Production: 44,26,729 Tonnes | Value: 2,32,806 Rs. Lakh
Crop: Blackgram    | 2012-13 | District: Sibsagar            | Area: 48,527* Hectares
Crop: Jute         | 2022-23 | District: Nowgong             | Area: 64,033* Hectares
"""

# Ground truth tuples: (location_id, metric_name, normalized_value, normalized_unit)
GROUND_TRUTH: Set[Tuple[str, str, float, str]] = {
    ("LGD_AS_00", "Area", 1769203.0, "ha"),
    ("LGD_AS_00", "Production", 4426729.0, "tonnes"),
    ("LGD_AS_00", "Value", 23280600000.0, "INR"),
    ("LGD_AS_300", "Area", 48527.0, "ha"),
    ("LGD_AS_297", "Area", 64033.0, "ha"),
}


def compute_f1(predicted: Set[Tuple[str, str, float, str]], gold: Set[Tuple[str, str, float, str]]) -> float:
    tp = len(predicted & gold)
    if tp == 0:
        return 0.0
    prec = tp / len(predicted)
    rec = tp / len(gold)
    return (2 * prec * rec) / (prec + rec)


def test_naive_regex_parser(text: str):
    """Naive regex extraction: fails on Indian comma grouping (17,69,203), footnote asterisks (*), Rs. Lakh, and historical LGD names."""
    preds: Set[Tuple[str, str, float, str]] = set()
    for line in text.strip().splitlines():
        m = re.search(r"(Area|Production|Value):\s*(\d+)\s*([A-Za-z.]+)", line)
        if m:
            preds.add(("LGD_AS_00", m.group(1), float(m.group(2)), m.group(3).lower()))
    return {"tool": "Naive_TextBlock_Parser (Raw Regex)", "f1": compute_f1(preds, GROUND_TRUTH), "extracted": len(preds)}


def test_geometric_cell_parser(text: str):
    """Cell-split parser without historical LGD resolution ('Sibsagar', 'Nowgong') or Rs. Lakh -> INR scaling."""
    preds: Set[Tuple[str, str, float, str]] = set()
    for line in text.strip().splitlines():
        cells = [c.strip() for c in line.split("|")]
        dist = "LGD_AS_00"
        for cell in cells:
            m = re.match(r"^(Area|Production|Value):\s*([\d,]+)\s*(Hectares|Tonnes|Rs\.\s*Lakh)$", cell)
            if m:
                val = float(m.group(2).replace(",", ""))
                unit = "ha" if m.group(3) == "Hectares" else ("tonnes" if m.group(3) == "Tonnes" else "Rs. Lakh")
                preds.add((dist, m.group(1), val, unit))
    return {"tool": "Geometric_Grid_Parser (No LGD/Self-Correction)", "f1": compute_f1(preds, GROUND_TRUTH), "extracted": len(preds)}


def test_hybrid_qwen_normalizer(text: str):
    """Full AISemanticExtractor + Agent3TaskNormalizer with footnote self-correction, LGD resolution, and SI unit scaling."""
    normalizer = Agent3TaskNormalizer()
    preds: Set[Tuple[str, str, float, str]] = set()
    for idx, line in enumerate(text.strip().splitlines(), 1):
        parts = [p.strip() for p in line.split("|")]
        row_dict = {}
        for p in parts:
            if ":" in p:
                k, v = [x.strip() for x in p.split(":", 1)]
                row_dict[k.lower()] = v
            else:
                row_dict["time_period"] = p
        for raw_rec in AISemanticExtractor.map_header_rows(
            row_dict, "benchmark.txt", f"Row={idx}", "SRC_01", "Document_PDF", "agent2_ingestion"
        ):
            norm = normalizer.normalize_record(raw_rec)
            preds.add((norm["location_id"], norm["metric_name"], norm["normalized_value"], norm["normalized_unit"]))
    return {"tool": "Hybrid_AISemantic_Agent3_Normalizer (Selected)", "f1": compute_f1(preds, GROUND_TRUTH), "extracted": len(preds)}


if __name__ == "__main__":
    print("=== LIVE OPEN-SOURCE TOOL COMPARISON ON ASSAM STATISTICAL TABLES ===")
    for fn in (test_naive_regex_parser, test_geometric_cell_parser, test_hybrid_qwen_normalizer):
        res = fn(SAMPLE_TABLE_TEXT)
        print(f"Tool: {res['tool']:<48} | Measured F1: {res['f1']:.3f} (Extracted={res['extracted']})")