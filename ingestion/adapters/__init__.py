"""Modular Source Adapters Registry."""
from ingestion.adapters.csv_adapter import CSVFeedAdapter
from ingestion.adapters.html_table_adapter import HTMLTableAdapter
from ingestion.adapters.pdf_table_adapter import PDFTableAdapter
from ingestion.adapters.text_adapter import UnstructuredTextAdapter
from ingestion.adapters.wms_gis_adapter import WMSGISAdapter
from ingestion.base_adapter import AdapterRegistry

def build_default_registry() -> AdapterRegistry:
    reg = AdapterRegistry()
    for cls in (CSVFeedAdapter, HTMLTableAdapter, PDFTableAdapter, UnstructuredTextAdapter, WMSGISAdapter):
        reg.register(cls)
    return reg
