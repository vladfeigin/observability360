provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

provider "docker" {
  registry_auth {
    address  = data.azurerm_container_registry.demo.login_server
    username = data.azurerm_container_registry.demo.admin_username
    password = data.azurerm_container_registry.demo.admin_password
  }
}

provider "azuread" {}

provider "kubernetes" {
  host = data.azurerm_kubernetes_cluster.demo.kube_config[0].host

  client_certificate     = base64decode(data.azurerm_kubernetes_cluster.demo.kube_config[0].client_certificate)
  client_key             = base64decode(data.azurerm_kubernetes_cluster.demo.kube_config[0].client_key)
  cluster_ca_certificate = base64decode(data.azurerm_kubernetes_cluster.demo.kube_config[0].cluster_ca_certificate)
}

provider "fabric" {}