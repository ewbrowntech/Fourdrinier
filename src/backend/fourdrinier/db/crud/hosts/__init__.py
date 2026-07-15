"""
__init__.py

Expose provider-neutral host aggregate persistence operations.
"""

from fourdrinier.db.crud.hosts.create_host import create_host
from fourdrinier.db.crud.hosts.delete_host import delete_host
from fourdrinier.db.crud.hosts.get_host import get_host
from fourdrinier.db.crud.hosts.list_hosts import list_hosts

__all__: list[str] = [
    "create_host",
    "delete_host",
    "get_host",
    "list_hosts",
]
