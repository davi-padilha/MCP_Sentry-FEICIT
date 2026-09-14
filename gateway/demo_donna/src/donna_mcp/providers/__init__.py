"""Adaptadores de calendario e e-mail."""

from .base import SecretaryProvider
from .factory import build_provider

__all__ = ["SecretaryProvider", "build_provider"]
