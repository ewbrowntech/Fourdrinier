#!/bin/bash
set -e

echo "======================================"
echo "Fourdrinier Kubernetes Setup Script"
echo "======================================"
echo

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Step 1: Applying Kubernetes manifests..."
kubectl apply -f "$SCRIPT_DIR/namespace.yaml"
kubectl apply -f "$SCRIPT_DIR/serviceaccount.yaml"
kubectl apply -f "$SCRIPT_DIR/role.yaml"
kubectl apply -f "$SCRIPT_DIR/rolebinding.yaml"
kubectl apply -f "$SCRIPT_DIR/secret-token.yaml"
echo "✓ All manifests applied successfully"
echo

echo "Step 2: Waiting for secret to be created..."
sleep 2
echo "✓ Secret ready"
echo

echo "Step 3: Creating credentials directory..."
mkdir -p "$PROJECT_ROOT/.k8s"
echo "✓ Directory created at $PROJECT_ROOT/.k8s"
echo

echo "Step 4: Extracting ServiceAccount token..."
kubectl get secret fourdrinier-backend-token -n minecraft -o jsonpath='{.data.token}' | base64 -d > "$PROJECT_ROOT/.k8s/token"
echo "✓ Token extracted to $PROJECT_ROOT/.k8s/token"
echo

echo "Step 5: Extracting CA certificate..."
kubectl get secret fourdrinier-backend-token -n minecraft -o jsonpath='{.data.ca\.crt}' | base64 -d > "$PROJECT_ROOT/.k8s/ca.crt"
echo "✓ CA certificate extracted to $PROJECT_ROOT/.k8s/ca.crt"
echo

echo "Step 6: Verifying setup..."
echo "  - Namespace: minecraft"
kubectl get namespace minecraft -o jsonpath='{.metadata.name}' && echo " ✓"
echo "  - ServiceAccount: fourdrinier-backend"
kubectl get serviceaccount fourdrinier-backend -n minecraft -o jsonpath='{.metadata.name}' && echo " ✓"
echo "  - Role: minecraft-manager"
kubectl get role minecraft-manager -n minecraft -o jsonpath='{.metadata.name}' && echo " ✓"
echo "  - RoleBinding: fourdrinier-backend-binding"
kubectl get rolebinding fourdrinier-backend-binding -n minecraft -o jsonpath='{.metadata.name}' && echo " ✓"
echo "  - Secret: fourdrinier-backend-token"
kubectl get secret fourdrinier-backend-token -n minecraft -o jsonpath='{.metadata.name}' && echo " ✓"
echo

echo "======================================"
echo "Setup completed successfully!"
echo "======================================"
echo
echo "Credentials extracted to:"
echo "  - Token: $PROJECT_ROOT/.k8s/token"
echo "  - CA Cert: $PROJECT_ROOT/.k8s/ca.crt"
echo
echo "Next steps:"
echo "  1. Update backend dependencies: cd backend && poetry install"
echo "  2. Update docker-compose.yml and .env as per migration plan"
echo "  3. Rebuild backend: docker compose build backend"
echo
