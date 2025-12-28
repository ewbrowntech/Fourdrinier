"""
config.py

@Author: Ethan Brown - ethan@ewbrowntech.com

Configuration settings for the FastAPI application.

Copyright (C) 2024 by Ethan Brown
All rights reserved. This file is part of the Fourdrinier project and is released under
the GPLv3 License. See the LICENSE file for more details.
"""

import os


PROJECT_NAME = "fourdrinier"
DB_URL: str = os.getenv("DB_URL", "sqlite+aiosqlite:///./db-data/fourdrinier.db")

# Kubernetes configuration
K8S_API_HOST: str = os.getenv("K8S_API_HOST", "https://127.0.0.1:6443")
K8S_TOKEN_PATH: str = os.getenv(
    "K8S_TOKEN_PATH", "/var/run/secrets/kubernetes.io/serviceaccount/token"
)
K8S_CA_CERT_PATH: str = os.getenv(
    "K8S_CA_CERT_PATH", "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
)
K8S_NAMESPACE: str = os.getenv("K8S_NAMESPACE", "minecraft")

# Minecraft server defaults
MINECRAFT_IMAGE: str = os.getenv("MINECRAFT_IMAGE", "itzg/minecraft-server:java21-alpine")
MINECRAFT_PVC_SIZE: str = os.getenv("MINECRAFT_PVC_SIZE", "5Gi")
MINECRAFT_STORAGE_CLASS: str = os.getenv("MINECRAFT_STORAGE_CLASS", "local-path")
MINECRAFT_CPU_REQUEST: str = os.getenv("MINECRAFT_CPU_REQUEST", "1000m")
MINECRAFT_CPU_LIMIT: str = os.getenv("MINECRAFT_CPU_LIMIT", "2000m")
MINECRAFT_MEMORY_REQUEST: str = os.getenv("MINECRAFT_MEMORY_REQUEST", "2Gi")
MINECRAFT_MEMORY_LIMIT: str = os.getenv("MINECRAFT_MEMORY_LIMIT", "4Gi")
