#!/bin/bash
set -e

echo "======================================"
echo "Fourdrinier Kubernetes Cleanup Script"
echo "======================================"
echo

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "WARNING: This will delete the 'minecraft' namespace and all resources within it!"
echo "This includes all running Minecraft servers, their data (PVCs), and services."
echo

read -p "Are you sure you want to continue? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]
then
    echo "Cleanup cancelled."
    exit 0
fi

echo "Step 1: Deleting all Minecraft servers (Pods, PVCs, Services)..."
kubectl delete pods --all -n minecraft --grace-period=0 --force 2>/dev/null || true
kubectl delete services --all -n minecraft 2>/dev/null || true
kubectl delete pvc --all -n minecraft 2>/dev/null || true
echo "✓ All server resources deleted"
echo

echo "Step 2: Deleting RBAC resources..."
kubectl delete rolebinding fourdrinier-backend-binding -n minecraft 2>/dev/null || true
kubectl delete role minecraft-manager -n minecraft 2>/dev/null || true
echo "✓ RBAC resources deleted"
echo

echo "Step 3: Deleting ServiceAccount and Secret..."
kubectl delete secret fourdrinier-backend-token -n minecraft 2>/dev/null || true
kubectl delete serviceaccount fourdrinier-backend -n minecraft 2>/dev/null || true
echo "✓ ServiceAccount and Secret deleted"
echo

echo "Step 4: Deleting namespace..."
kubectl delete namespace minecraft 2>/dev/null || true
echo "✓ Namespace deleted"
echo

echo "Step 5: Removing local credential files..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
rm -rf "$PROJECT_ROOT/.k8s"
echo "✓ Local credentials removed"
echo

echo "======================================"
echo "Cleanup completed successfully!"
echo "======================================"
echo
echo "To recreate the infrastructure, run:"
echo "  ./k8s/setup.sh"
echo
