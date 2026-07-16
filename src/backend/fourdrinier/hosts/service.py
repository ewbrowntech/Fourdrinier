"""
service.py

Coordinate provider-neutral host persistence and remote operations.
"""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.core.secrets import PlaintextSecret, SecretEncryptor
from fourdrinier.db.crud import hosts as hosts_crud
from fourdrinier.db.crud import ssh_keypairs as keypairs_crud
from fourdrinier.db.models import (
    DockerHostDetails,
    Host,
    KubernetesHostDetails,
    SSHKeypair,
)
from fourdrinier.db.schemas.host import DockerHostCreate, HostCreate, KubernetesHostCreate
from fourdrinier.hosts.drivers import HostDriver, HostDriverRegistry
from fourdrinier.hosts.errors import (
    HostKeypairNotFoundError,
    HostNameConflictError,
    HostNotFoundError,
    HostProviderMismatchError,
)
from fourdrinier.hosts.types import HostId, HostPingResult, HostType


def _is_host_name_conflict(exc: IntegrityError) -> bool:
    original: BaseException = exc.orig
    message: str = str(original).lower()
    return "uq_hosts_name" in message or "unique constraint failed: hosts.name" in message


class HostService:
    """Implement host use cases across persistence and provider boundaries."""

    def __init__(
        self,
        session: AsyncSession,
        drivers: HostDriverRegistry,
        secret_encryptor: SecretEncryptor,
    ) -> None:
        """Initialize the service with its transaction and operation dependencies.

        Args:
            session: Session that owns transactions for host write operations.
            drivers: Registry used to select a provider for remote operations.
            secret_encryptor: Encryptor for credentials stored with host details.
        """
        self._session: AsyncSession = session
        self._drivers: HostDriverRegistry = drivers
        self._secret_encryptor: SecretEncryptor = secret_encryptor

    def _build_host(self, request: HostCreate) -> Host:
        if isinstance(request, DockerHostCreate):
            if request.type != HostType.DOCKER.value:
                raise HostProviderMismatchError(
                    "Docker host details must declare the docker provider",
                    provider=HostType.DOCKER,
                )
            docker_details: DockerHostDetails = DockerHostDetails(
                address=request.address,
                port=request.port,
                username=request.username,
                keypair_id=request.keypair_id,
            )
            docker_host: Host = Host(
                type=HostType.DOCKER,
                name=request.name,
                enabled=request.enabled,
                labels=request.labels,
                docker_details=docker_details,
            )
            return docker_host

        if isinstance(request, KubernetesHostCreate):
            if request.type != HostType.KUBERNETES.value:
                raise HostProviderMismatchError(
                    "Kubernetes host details must declare the kubernetes provider",
                    provider=HostType.KUBERNETES,
                )
            token_encrypted: bytes = self._secret_encryptor.encrypt(
                PlaintextSecret(request.token.encode())
            )
            kubernetes_details: KubernetesHostDetails = KubernetesHostDetails(
                api_url=request.api_url,
                ca_cert_pem=request.ca_cert_pem,
                token_encrypted=token_encrypted,
                namespace=request.namespace,
            )
            kubernetes_host: Host = Host(
                type=HostType.KUBERNETES,
                name=request.name,
                enabled=request.enabled,
                labels=request.labels,
                kubernetes_details=kubernetes_details,
            )
            return kubernetes_host

        raise HostProviderMismatchError(
            f"unsupported host creation details {type(request).__name__}",
        )

    async def _get_required(self, host_id: HostId) -> Host:
        host: Host | None = await hosts_crud.get_host(self._session, host_id)
        if host is None:
            raise HostNotFoundError(f"host {host_id} not found")
        return host

    async def create(self, request: HostCreate) -> Host:
        """Create a host and its matching provider details atomically.

        Args:
            request: Validated provider-specific host creation request.

        Returns:
            The newly persisted host aggregate.

        Raises:
            HostKeypairNotFoundError: If a Docker host selects an unknown SSH keypair.
            HostNameConflictError: If the requested host name already exists.
            HostProviderMismatchError: If details declare the wrong provider.
            SecretError: If provider credentials cannot be encrypted.
        """
        try:
            if isinstance(request, DockerHostCreate):
                keypair: SSHKeypair | None = await keypairs_crud.get_keypair(
                    self._session,
                    request.keypair_id,
                )
                if keypair is None:
                    raise HostKeypairNotFoundError(
                        f"keypair {request.keypair_id} not found",
                        provider=HostType.DOCKER,
                    )
            host: Host = self._build_host(request)
            created: Host = await hosts_crud.create_host(self._session, host)
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            if _is_host_name_conflict(exc):
                raise HostNameConflictError(
                    f"host with name {request.name!r} already exists",
                    provider=HostType(request.type),
                ) from exc
            raise
        except Exception:
            await self._session.rollback()
            raise
        return created

    async def get(self, host_id: HostId) -> Host:
        """Get a host aggregate by its provider-neutral identifier.

        Args:
            host_id: Identifier of the requested host.

        Returns:
            The matching host with its provider details loaded.

        Raises:
            HostNotFoundError: If the requested host does not exist.
        """
        host: Host = await self._get_required(host_id)
        return host

    async def list(self, host_type: HostType | None = None) -> list[Host]:
        """List hosts, optionally restricted to one provider type.

        Args:
            host_type: Provider to include, or ``None`` to include all hosts.

        Returns:
            Matching host aggregates in persistence-defined order.
        """
        hosts: list[Host] = await hosts_crud.list_hosts(self._session, host_type)
        return hosts

    async def delete(self, host_id: HostId) -> None:
        """Delete a host and its owned provider details atomically.

        Args:
            host_id: Identifier of the host to delete.

        Raises:
            HostNotFoundError: If the requested host does not exist.
        """
        try:
            host: Host = await self._get_required(host_id)
            await hosts_crud.delete_host(self._session, host)
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise

    async def ping(self, host_id: HostId) -> HostPingResult:
        """Check a host through its provider and persist successful observation state.

        Args:
            host_id: Identifier of the host to check.

        Returns:
            Provider-neutral observations from the successful check.

        Raises:
            HostNotFoundError: If the requested host does not exist.
            HostError: If driver selection or the remote check fails.
        """
        try:
            host: Host = await self._get_required(host_id)
            driver: HostDriver = self._drivers.for_host(host)
            result: HostPingResult = await driver.ping(host)
            host.last_seen_at = result.observed_at
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise
        return result


__all__: list[str] = ["HostService"]
