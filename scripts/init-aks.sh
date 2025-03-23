#!/bin/bash

# Check if all required arguments are passed
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <subscription-id> <resource-group> <aks-cluster-name>"
    exit 1
fi

# Input parameters
SUBSCRIPTION_ID=$1
RESOURCE_GROUP=$2
AKS_CLUSTER_NAME=$3

# Set the subscription and get AKS credentials
az account set --subscription "$SUBSCRIPTION_ID"
az aks get-credentials --resource-group "$RESOURCE_GROUP" --name "$AKS_CLUSTER_NAME" --overwrite-existing

# Namespace
NAMESPACE="online-store"

# Delete deployments
kubectl delete deploy/online-store-order -n "$NAMESPACE"
kubectl delete deploy/online-store-cart -n "$NAMESPACE"
kubectl delete deploy/online-store-ui -n "$NAMESPACE"
kubectl delete deploy/online-store-user -n "$NAMESPACE"
kubectl delete deploy/online-store-product -n "$NAMESPACE"

# Delete persistent volume claim
kubectl delete pvc/online-store-db-pvc -n "$NAMESPACE"

terraform apply -auto-approve -var-file="../terraform.tfvars"