"""PDF Table & Document Adapter."""
import io
from importlib import import_module
from typing import List, Optional
try:
    pdfplumber = import_module("pdfplumber")
except ImportError:
    pdfplumber = None
from ingestion.adapters.ai_table_mapper import AISchemaMapper
from ingestion.ai_runtime import AIRuntime
from ingestion.base_adapter import BaseSourceAdapter
from ingestion.http_client import SafeHTTPClient
from ingestion.models import RawFetchResult, SourceConfig, SourceRecord

class PDFTableAdapter(BaseSourceAdapter):
    adapter_type = "pdf_table"
    def __init__(self, http_client: Optional[SafeHTTPClient] = None, ai_runtime: Optional[AIRuntime] = None, max_pages: Optional[int] = None) -> None:
        self.http = http_client or SafeHTTPClient()
        self.mapper = AISchemaMapper(ai_runtime=ai_runtime)
        self.max_pages = max_pages
    def fetch(self, config: SourceConfig, etag: Optional[str] = None, last_modified: Optional[str] = None) -> RawFetchResult:
        return self.http.fetch(config.source_id, config.url, etag=etag, last_modified=last_modified)
    def parse(self, config: SourceConfig, raw: RawFetchResult) -> List[SourceRecord]:
        if raw.not_modified or not raw.raw_bytes:
            return []
        if pdfplumber is None:
            raise RuntimeError("pdfplumber is required for PDFTableAdapter.")
        records: List[SourceRecord] = []
        with pdfplumber.open(io.BytesIO(raw.raw_bytes)) as pdf:
            pages = pdf.pages[:self.max_pages] if self.max_pages else pdf.pages
            for p_idx, page in enumerate(pages, 1):
                page_recs: List[SourceRecord] = []
                for t_idx, tbl in enumerate(page.extract_tables() or [], 1):
                    if not tbl or len(tbl) < 2: continue
                    headers = [str(h or "").strip() for h in tbl[0]]
                    if not any(headers): continue
                    trows = [dict(zip(headers, [str(c or "").strip() for c in r])) for r in tbl[1:] if len(r) == len(headers) and any(str(c or "").strip() for c in r)]
                    if trows:
                        page_recs.extend(self.mapper.rows_to_source_records(config, trows, f"Page={p_idx};Table={t_idx}", raw.fetched_at_utc, raw.source_url))
                if not page_recs:
                    page_recs.extend(self.mapper.extract_unstructured_text(config, page.extract_text() or "", f"Page={p_idx}", raw.fetched_at_utc, raw.source_url))
                records.extend(page_recs)
        return records
