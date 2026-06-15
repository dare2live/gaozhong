"""Registry-driven external data source acquisition utilities."""
from __future__ import annotations

from .fetcher import acquire_source
from .registry import AttachmentSpec, SourceRegistry, SourceSpec, load_registry

__all__ = [
    "AttachmentSpec",
    "SourceRegistry",
    "SourceSpec",
    "acquire_source",
    "load_registry",
]
