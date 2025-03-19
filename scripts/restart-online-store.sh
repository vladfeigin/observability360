#!/bin/bash
# Script to restart all deployments in the specified Kubernetes namespace

NAMESPACE="online-store"

echo "Fetching deployments in namespace: $NAMESPACE"
DEPLOYMENTS=$(kubectl get deployments -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}')

if [ -z "$DEPLOYMENTS" ]; then
    echo "No deployments found in namespace $NAMESPACE"
    exit 1
fi

for deploy in $DEPLOYMENTS; do
    echo "Restarting deployment: $deploy"
    kubectl rollout restart deployment/"$deploy" -n "$NAMESPACE"
done

echo "Restart commands issued for all deployments."