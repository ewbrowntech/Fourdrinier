"""
kubernetes_client.py

Kubernetes client initialization and configuration

Copyright (C) 2024 by Ethan Brown
All rights reserved. This file is part of the Fourdrinier project and is released under
the GPLv3 License. See the LICENSE file for more details.
"""

from kubernetes import client

from fourdrinier.core.config import (
    K8S_API_HOST,
    K8S_CA_CERT_PATH,
    K8S_NAMESPACE,
    K8S_TOKEN_PATH,
)


def get_k8s_client() -> tuple[client.CoreV1Api, str]:
    """
    Initialize and return Kubernetes CoreV1Api client with token authentication

    Returns:
        Tuple of (CoreV1Api client, namespace)
    """
    # Read ServiceAccount token
    with open(K8S_TOKEN_PATH, "r") as f:
        token = f.read().strip()

    # Configure client
    configuration = client.Configuration()
    configuration.host = K8S_API_HOST
    configuration.api_key = {"authorization": f"Bearer {token}"}
    configuration.ssl_ca_cert = K8S_CA_CERT_PATH

    # For local development: disable SSL hostname verification
    # The CA cert is still verified, but hostname mismatch is ignored
    configuration.verify_ssl = True
    configuration.assert_hostname = False

    # Create API client
    api_client = client.ApiClient(configuration)
    v1 = client.CoreV1Api(api_client)

    return v1, K8S_NAMESPACE
