"""Phase 2 Unit & Failure Scenario Tests."""
import os, tempfile, unittest
from unittest.mock import MagicMock, patch
from ingestion.adapters import build_default_registry
from ingestion.adapters.csv_adapter import CSVFeedAdapter
from ingestion.adapters.html_table_adapter import HTMLTableAdapter
from ingestion.adapters.text_adapter import UnstructuredTextAdapter
from ingestion.http_client import SafeHTTPClient
from ingestion.models import AIResponse, RawFetchResult, SourceConfig
from ingestion.storage import utc_now_iso

class _FakeAI:
    def __init__(self, response: AIResponse):
        self.response, self.calls = response, 0
    def call_json(self, agent_name, system_prompt, user_prompt):
        self.calls += 1
        return self.response

class TestPhase2HTTPAndAdapters(unittest.TestCase):
    def test_registry_has_all_five_adapters(self):
        self.assertEqual(build_default_registry().list_adapters(), ["csv_feed", "html_table", "pdf_table", "unstructured_text", "wms_gis"])

    @patch("ingestion.http_client.socket.getaddrinfo")
    @patch("ingestion.http_client.requests.get")
    def test_http_client_200_304_ssrf_and_max_bytes(self, mock_get, mock_dns):
        mock_dns.side_effect = lambda host, port: [(2, 1, 6, "", ("127.0.0.1" if host == "internal.local" else "93.184.216.34", 0))]
        client = SafeHTTPClient(max_retries=1, max_bytes=1024)

        r200 = MagicMock(status_code=200, headers={"Content-Type": "text/csv", "ETag": '"e1"'})
        r200.iter_content.return_value = [b"crop,value\nRice,100\n"]
        mock_get.return_value = r200
        res = client.fetch("SRC_01", "https://example.org/data.csv")
        self.assertEqual(res.http_status, 200)
        self.assertEqual(res.etag, '"e1"')

        mock_get.return_value = MagicMock(status_code=304, headers={"ETag": '"e1"'})
        self.assertTrue(client.fetch("SRC_01", "https://example.org/data.csv", etag='"e1"').not_modified)

        mock_get.return_value = MagicMock(status_code=302, headers={"Location": "http://internal.local/secret"})
        self.assertIn("SSRFBlockedError", client.fetch("SRC_01", "https://example.org/redirect").error_message)

        r_big = MagicMock(status_code=200, headers={"Content-Type": "text/csv"})
        r_big.iter_content.return_value = [b"x" * 2048]
        mock_get.return_value = r_big
        self.assertIn("PayloadTooLargeError", client.fetch("SRC_01", "https://example.org/big.csv").error_message)

    def test_csv_adapter_ai_schema_once_wide_format(self):
        csv_bytes = b"CropName,DistrictName,Year,Area_ha,Prod_MT\nRice (Paddy),Sibsagar,2024-25,114200*,250000\n"
        fake_ai = _FakeAI(AIResponse({"crop_col": "CropName", "variety_col": None, "district_col": "DistrictName", "time_period_col": "Year", "metric_name_col": None, "raw_value_col": None, "raw_unit_col": None, "wide_metric_cols": [{"col": "Area_ha", "metric_name": "Area", "unit": "ha"}, {"col": "Prod_MT", "metric_name": "Production", "unit": "MT"}]}, "{}", "groq", "openai/gpt-oss-120b", 120, 310.0, False))
        cfg = SourceConfig("SRC_01", "DES", "local://s.csv", "Document_PDF", "csv_feed", "agent2_ingestion")
        raw = RawFetchResult("SRC_01", cfg.url, utc_now_iso(), 200, False, csv_bytes, "text/csv", content_sha256="abc")
        recs = CSVFeedAdapter(ai_runtime=fake_ai).parse(cfg, raw)
        self.assertEqual(fake_ai.calls, 1)
        self.assertEqual(len(recs), 2)
        self.assertEqual(recs[0].raw_value, "114200*")

    def test_html_table_adapter_local_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as tf:
            tf.write("<html><body><table><tr><th>Crop</th><th>Variety</th><th>District</th><th>Period</th><th>Metric</th><th>Value</th><th>Unit</th></tr><tr><td>Wheat</td><td>DBW-187</td><td>Kamrup</td><td>2025</td><td>Yield</td><td>34.0</td><td>q/ha</td></tr></table></body></html>")
            fp = tf.name
        try:
            cfg = SourceConfig("SRC_06", "AAU", fp, "Web_Portal", "html_table", "agent2_ingestion")
            adapter = HTMLTableAdapter(ai_runtime=_FakeAI(AIResponse(None, "", "none", "deterministic_fallback", 0, 0.0, True)))
            recs = adapter.parse(cfg, adapter.fetch(cfg))
            self.assertEqual(len(recs), 1)
            self.assertEqual(recs[0].crop_name, "Wheat")
        finally:
            os.remove(fp)

    def test_unstructured_text_assamese_ai_and_fallback(self):
        txt = "শস্য: শালি ধান | জাত: ৰঞ্জিত চাব-১ | জিলা: যোৰহাট | বৰ্ষ: 2025-26 | উৎপাদন ক্ষমতা: ৫৪.৫ কুইণ্টল/হেক্টৰ\n".encode("utf-8")
        cfg = SourceConfig("SRC_07", "KVK", "local://as.txt", "Web_Portal", "unstructured_text", "agent2_ingestion")
        raw = RawFetchResult("SRC_07", cfg.url, utc_now_iso(), 200, False, txt, "text/plain", content_sha256="sha")
        recs = UnstructuredTextAdapter(ai_runtime=_FakeAI(AIResponse(None, "", "none", "deterministic_fallback", 0, 0.0, True))).parse(cfg, raw)
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0].raw_value, "54.5")

if __name__ == "__main__":
    unittest.main()
