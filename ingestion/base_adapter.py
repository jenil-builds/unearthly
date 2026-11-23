"""Common Source Adapter Interface and Modular Adapter Registry."""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Type
from ingestion.models import RawFetchResult, SourceConfig, SourceRecord

class BaseSourceAdapter(ABC):
    adapter_type: str = ""

    @abstractmethod
    def fetch(self, config: SourceConfig, etag: Optional[str] = None, last_modified: Optional[str] = None) -> RawFetchResult:
        """Fetches raw bytes from the real external source feed."""

    @abstractmethod
    def parse(self, config: SourceConfig, raw: RawFetchResult) -> List[SourceRecord]:
        """Parses raw source bytes into attributed SourceRecord items without fabrication."""

    def health_check(self, config: SourceConfig) -> bool:
        res = self.fetch(config)
        return res.error_message is None and (res.http_status in (200, 304) or res.http_status is None)

class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: Dict[str, Type[BaseSourceAdapter]] = {}

    def register(self, adapter_cls: Type[BaseSourceAdapter]) -> None:
        if not adapter_cls.adapter_type:
            raise ValueError(f"Adapter {adapter_cls.__name__} must define a non-empty adapter_type")
        self._adapters[adapter_cls.adapter_type] = adapter_cls

    def get(self, adapter_type: str) -> BaseSourceAdapter:
        if adapter_type not in self._adapters:
            raise KeyError(f"No adapter registered for '{adapter_type}'. Available: {sorted(self._adapters.keys())}")
        return self._adapters[adapter_type]()

    def list_adapters(self) -> List[str]:
        return sorted(self._adapters.keys())
