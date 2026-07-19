"""
__init__.py

Expose logical server persistence operations.
"""

from fourdrinier.db.crud.servers.create_server import create_server
from fourdrinier.db.crud.servers.delete_server import delete_server
from fourdrinier.db.crud.servers.get_server import get_server
from fourdrinier.db.crud.servers.list_servers import list_servers
from fourdrinier.db.crud.servers.update_server import update_server

__all__: list[str] = [
    "create_server",
    "delete_server",
    "get_server",
    "list_servers",
    "update_server",
]
