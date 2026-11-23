"""SSRF-Safe HTTP & Local Source Fetch Client (ingestion/http_client.py)."""
import hashlib, ipaddress, os, socket, time
from typing import Optional
from urllib.parse import urljoin, urlparse
try:
    import requests
except ImportError:
    requests = None

from ingestion.models import RawFetchResult
from ingestion.storage import utc_now_iso

class SSRFBlockedError(ValueError):
    pass

class PayloadTooLargeError(ValueError):
    pass

class SafeHTTPClient:
    USER_AGENT = "AgriAgent-Assam/2.1 (+https://github.com/jenil-builds/unearthly)"

    def __init__(self, timeout_sec: float = 20.0, max_retries: int = 2, max_redirects: int = 5, max_bytes: int = 25 * 1024 * 1024, verify_ssl: bool = True) -> None:
        self.timeout_sec = timeout_sec
        self.max_retries = max_retries
        self.max_redirects = max_redirects
        self.max_bytes = max_bytes
        self.verify_ssl = verify_ssl

    @staticmethod
    def validate_safe_url(url: str) -> urlparse:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise SSRFBlockedError(f"Invalid or unsupported URL scheme: {url}")
        try:
            addr_info = socket.getaddrinfo(parsed.hostname, None)
        except socket.gaierror as exc:
            raise SSRFBlockedError(f"DNS resolution failed for '{url}': {exc}") from exc
        for item in addr_info:
            ip_obj = ipaddress.ip_address(item[4][0])
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_multicast or ip_obj.is_reserved or ip_obj.is_unspecified:
                raise SSRFBlockedError(f"Blocked non-public IP target ({ip_obj}) for URL: {url}")
        return parsed

    def _fetch_local(self, source_id: str, url_or_path: str) -> RawFetchResult:
        fetched_at = utc_now_iso()
        local_path = url_or_path[len("local://"):] if url_or_path.startswith("local://") else url_or_path
        if not os.path.isfile(local_path):
            return RawFetchResult(source_id=source_id, source_url=url_or_path, fetched_at_utc=fetched_at, http_status=None, not_modified=False, error_message=f"Local file not found: {local_path}")
        size = os.path.getsize(local_path)
        if size > self.max_bytes:
            return RawFetchResult(source_id=source_id, source_url=url_or_path, fetched_at_utc=fetched_at, http_status=None, not_modified=False, error_message=f"Local file exceeds max_bytes ({size} > {self.max_bytes})")
        with open(local_path, "rb") as f:
            data = f.read()
        ext = os.path.splitext(local_path)[1].lower()
        ctype_map = {".csv": "text/csv", ".html": "text/html", ".htm": "text/html", ".pdf": "application/pdf", ".json": "application/json", ".xml": "application/xml", ".txt": "text/plain"}
        return RawFetchResult(source_id=source_id, source_url=url_or_path, fetched_at_utc=fetched_at, http_status=200, not_modified=False, raw_bytes=data, content_type=ctype_map.get(ext, "application/octet-stream"), content_sha256=hashlib.sha256(data).hexdigest())

    def fetch(self, source_id: str, url: str, etag: Optional[str] = None, last_modified: Optional[str] = None) -> RawFetchResult:
        if not url.startswith(("http://", "https://")):
            return self._fetch_local(source_id, url)
        fetched_at = utc_now_iso()
        if requests is None:
            return RawFetchResult(source_id=source_id, source_url=url, fetched_at_utc=fetched_at, http_status=None, not_modified=False, error_message="The 'requests' library is required for HTTP fetching.")
        headers = {"User-Agent": self.USER_AGENT}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified
        last_err, last_status = None, None
        for attempt in range(self.max_retries + 1):
            current_url = url
            try:
                resp = None
                for hop in range(self.max_redirects + 1):
                    self.validate_safe_url(current_url)
                    resp = requests.get(current_url, headers=headers, timeout=self.timeout_sec, allow_redirects=False, stream=True, verify=self.verify_ssl)
                    last_status = resp.status_code
                    if resp.status_code in (301, 302, 303, 307, 308):
                        loc = resp.headers.get("Location")
                        resp.close()
                        if not loc:
                            raise ValueError(f"Redirect ({resp.status_code}) missing Location header")
                        current_url = urljoin(current_url, loc)
                        if hop == self.max_redirects:
                            raise ValueError(f"Exceeded max_redirects ({self.max_redirects})")
                        continue
                    break
                assert resp is not None
                if resp.status_code == 304:
                    resp.close()
                    return RawFetchResult(source_id=source_id, source_url=current_url, fetched_at_utc=fetched_at, http_status=304, not_modified=True, etag=resp.headers.get("ETag") or etag, last_modified=resp.headers.get("Last-Modified") or last_modified)
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    resp.close()
                    last_err = f"HTTP {resp.status_code}"
                    time.sleep(min(2.0 ** attempt, 4.0))
                    continue
                resp.raise_for_status()
                chunks, total = [], 0
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        total += len(chunk)
                        if total > self.max_bytes:
                            resp.close()
                            raise PayloadTooLargeError(f"Response exceeded max_bytes ({self.max_bytes})")
                        chunks.append(chunk)
                resp.close()
                raw_bytes = b"".join(chunks)
                return RawFetchResult(source_id=source_id, source_url=current_url, fetched_at_utc=fetched_at, http_status=resp.status_code, not_modified=False, raw_bytes=raw_bytes, content_type=resp.headers.get("Content-Type", "").lower(), etag=resp.headers.get("ETag"), last_modified=resp.headers.get("Last-Modified"), content_sha256=hashlib.sha256(raw_bytes).hexdigest())
            except (SSRFBlockedError, PayloadTooLargeError) as exc:
                return RawFetchResult(source_id=source_id, source_url=current_url, fetched_at_utc=fetched_at, http_status=last_status, not_modified=False, error_message=f"{type(exc).__name__}: {exc}")
            except Exception as exc:
                last_err = f"{type(exc).__name__}: {exc}"
                if attempt < self.max_retries:
                    time.sleep(min(2.0 ** attempt, 4.0))
        return RawFetchResult(source_id=source_id, source_url=url, fetched_at_utc=fetched_at, http_status=last_status, not_modified=False, error_message=last_err or "Unknown HTTP fetch failure")
