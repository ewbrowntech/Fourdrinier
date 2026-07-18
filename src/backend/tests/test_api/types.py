"""
types.py

Define shared callable and JSON types for API integration tests.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

type JsonObject = dict[str, Any]
type HostFactory = Callable[..., Awaitable[JsonObject]]
type KeypairFactory = Callable[[str], Awaitable[JsonObject]]
type ServerFactory = Callable[..., Awaitable[JsonObject]]
