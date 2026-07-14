"""
__init__.py

Expose the Docker-over-SSH host integration.
"""

from fourdrinier.hosts.docker.driver import DockerHostDriver

__all__: list[str] = ["DockerHostDriver"]
