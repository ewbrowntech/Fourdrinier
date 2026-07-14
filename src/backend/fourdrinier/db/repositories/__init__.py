"""
__init__.py

Expose repositories that persist application aggregates.
"""

from fourdrinier.db.repositories.hosts import HostRepository

__all__: list[str] = ["HostRepository"]
