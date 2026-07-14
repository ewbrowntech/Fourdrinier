"""
__init__.py

Expose the Kubernetes host integration.
"""

from fourdrinier.hosts.kubernetes.driver import KubernetesHostDriver

__all__: list[str] = ["KubernetesHostDriver"]
