resource "azurerm_kubernetes_cluster" "demo" {
  name                = "${var.base_name}-aks"
  location            = var.region
  resource_group_name = azurerm_resource_group.demo.name
  dns_prefix          = "${var.base_name}-dns"

  default_node_pool {
    name                 = "default"
    node_count           = 1
    vm_size              = "Standard_DS2_v2"
    auto_scaling_enabled = true
    min_count            = 1
    max_count            = 3

    upgrade_settings {
      drain_timeout_in_minutes      = 0
      max_surge                     = "10%"
      node_soak_duration_in_minutes = 0
    }
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin    = "azure"
    load_balancer_sku = "standard"
  }

  tags = {
    environment = "demo"
  }
}

resource "azurerm_kubernetes_cluster_node_pool" "workloads" {
  name                  = "workloadpool"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.demo.id
  vm_size               = "Standard_DS3_v2"
  node_count            = 2
  max_pods              = 110
  os_disk_size_gb       = 30
  os_type               = "Linux"

  auto_scaling_enabled = true
  min_count            = 1
  max_count            = 3

  node_labels = {
    environment = "workloadpool"
  }

  lifecycle {
    ignore_changes = [ node_count ]
  }
}

resource "azurerm_role_assignment" "acrpull_role" {
  scope                            = azurerm_container_registry.demo.id
  role_definition_name             = "AcrPull"
  principal_id                     = azurerm_kubernetes_cluster.demo.identity[0].principal_id
  skip_service_principal_aad_check = true
}