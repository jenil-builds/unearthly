"""Live Mandi & WMS Geospatial Adapter."""
from typing import List, Optional
from ingestion.adapters.ai_table_mapper import AISchemaMapper
from ingestion.adapters.html_table_adapter import HTMLTableAdapter
from ingestion.ai_runtime import AIRuntime
from ingestion.base_adapter import BaseSourceAdapter
from ingestion.http_client import SafeHTTPClient
from ingestion.models import RawFetchResult, SourceConfig, SourceRecord

class WMSGISAdapter(BaseSourceAdapter):
    adapter_type = "wms_gis"
    def __init__(self, http_client: Optional[SafeHTTPClient] = None, ai_runtime: Optional[AIRuntime] = None) -> None:
        self.http = http_client or SafeHTTPClient()
        self.mapper = AISchemaMapper(ai_runtime=ai_runtime)
        self.html_helper = HTMLTableAdapter(http_client=self.http, ai_runtime=ai_runtime)
    def fetch(self, config: SourceConfig, etag: Optional[str] = None, last_modified: Optional[str] = None) -> RawFetchResult:
        return self.http.fetch(config.source_id, config.url, etag=etag, last_modified=last_modified)
    def parse(self, config: SourceConfig, raw: RawFetchResult) -> List[SourceRecord]:
        if raw.not_modified or not raw.raw_bytes:
            return []
        if "html" in raw.content_type:
            return self.html_helper.parse(config, raw)
        return self.mapper.extract_unstructured_text(config, raw.raw_bytes.decode("utf-8", errors="replace"), f"WMS={config.source_id}", raw.fetched_at_utc, raw.source_url)
