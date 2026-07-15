"""
__init__.py

Expose Kubernetes host operations used by the driver.
"""

from fourdrinier.hosts.kubernetes.operations.ping import ping

__all__: list[str] = ["ping"]
