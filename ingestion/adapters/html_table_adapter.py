"""HTML Table & Portal Adapter."""
from html.parser import HTMLParser
import re
from typing import Dict, List, Optional
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
from ingestion.adapters.ai_table_mapper import AISchemaMapper
from ingestion.ai_runtime import AIRuntime
from ingestion.base_adapter import BaseSourceAdapter
from ingestion.http_client import SafeHTTPClient
from ingestion.models import RawFetchResult, SourceConfig, SourceRecord

class _StdlibTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: List[List[List[str]]] = []
        self._in_table = self._in_row = self._in_cell = False
        self._cur_table: List[List[str]] = []
        self._cur_row: List[str] = []
        self._cur_cell: List[str] = []
    def handle_starttag(self, tag: str, attrs) -> None:
        t = tag.lower()
        if t == "table": self._in_table, self._cur_table = True, []
        elif t == "tr" and self._in_table: self._in_row, self._cur_row = True, []
        elif t in ("td", "th") and self._in_row: self._in_cell, self._cur_cell = True, []
    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in ("td", "th") and self._in_cell:
            self._cur_row.append("".join(self._cur_cell).strip()); self._in_cell = False
        elif t == "tr" and self._in_row:
            if self._cur_row: self._cur_table.append(self._cur_row)
            self._in_row = False
        elif t == "table" and self._in_table:
            if self._cur_table: self.tables.append(self._cur_table)
            self._in_table = False
    def handle_data(self, data: str) -> None:
        if self._in_cell: self._cur_cell.append(data)

class HTMLTableAdapter(BaseSourceAdapter):
    adapter_type = "html_table"
    def __init__(self, http_client: Optional[SafeHTTPClient] = None, ai_runtime: Optional[AIRuntime] = None) -> None:
        self.http = http_client or SafeHTTPClient()
        self.mapper = AISchemaMapper(ai_runtime=ai_runtime)
    def fetch(self, config: SourceConfig, etag: Optional[str] = None, last_modified: Optional[str] = None) -> RawFetchResult:
        return self.http.fetch(config.source_id, config.url, etag=etag, last_modified=last_modified)
    @staticmethod
    def _extract_tables(html_text: str) -> List[List[List[str]]]:
        if BeautifulSoup is not None:
            soup = BeautifulSoup(html_text, "html.parser")
            out = []
            for table in soup.find_all("table"):
                rows = [[c.get_text(strip=True) for c in tr.find_all(["td", "th"])] for tr in table.find_all("tr")]
                rows = [r for r in rows if r]
                if rows: out.append(rows)
            return out
        p = _StdlibTableParser(); p.feed(html_text); return p.tables
    def parse(self, config: SourceConfig, raw: RawFetchResult) -> List[SourceRecord]:
        if raw.not_modified or not raw.raw_bytes:
            return []
        html_text = raw.raw_bytes.decode("utf-8", errors="replace")
        records: List[SourceRecord] = []
        for t_idx, rows in enumerate(self._extract_tables(html_text), 1):
            if len(rows) < 2 or not any(rows[0]):
                continue
            headers = rows[0]
            table_rows = [dict(zip(headers, cols)) for cols in rows[1:] if len(cols) == len(headers) and any(cols)]
            if table_rows:
                records.extend(self.mapper.rows_to_source_records(config, table_rows, f"HTML={config.source_id};Table={t_idx}", raw.fetched_at_utc, raw.source_url))
        if not records:
            visible = BeautifulSoup(html_text, "html.parser").get_text("\n", strip=True) if BeautifulSoup else re.sub(r"<[^>]+>", "\n", html_text)
            records.extend(self.mapper.extract_unstructured_text(config, visible, f"HTML={config.source_id}", raw.fetched_at_utc, raw.source_url))
        return records
