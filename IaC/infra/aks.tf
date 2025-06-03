locals {
  aks_name = "${var.base_name}-aks"
}

resource "azurerm_kubernetes_cluster" "demo" {
  name                = local.aks_name
  location            = var.region
  resource_group_name = azurerm_resource_group.demo.name
  dns_prefix          = "${var.base_name}-dns"

  default_node_pool {
    name                        = "default"
    node_count                  = 1
    vm_size                     = "Standard_DS2_v2"
    auto_scaling_enabled        = true
    min_count                   = 1
    max_count                   = 3
    vnet_subnet_id              = azurerm_subnet.aks.id
    temporary_name_for_rotation = "tmpdefault1"

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
    network_plugin = "azure"
    dns_service_ip = var.aks_dns_service_ip
    service_cidr   = var.aks_service_cidr
  }

  lifecycle {
    ignore_changes = [default_node_pool.0.node_count]
  }
}

resource "azurerm_role_assignment" "acrpull_role" {
  scope                = azurerm_container_registry.demo.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_kubernetes_cluster.demo.kubelet_identity[0].object_id
}

# AKS Node Pool
resource "azurerm_kubernetes_cluster_node_pool" "workloads" {
  name                  = "workloadpool"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.demo.id
  vm_size               = "Standard_DS3_v2"
  node_count            = 2
  max_pods              = 110
  os_disk_size_gb       = 30
  os_type               = "Linux"

  auto_scaling_enabled = true
  min_count            = 2
  max_count            = 3
  vnet_subnet_id       = azurerm_subnet.aks.id

  node_labels = {
    environment = "workloadpool"
  }

  lifecycle {
    ignore_changes = [node_count]
  }
}

# Monitoring
data "azurerm_monitor_diagnostic_categories" "aks" {
  resource_id = azurerm_kubernetes_cluster.demo.id
}

resource "azurerm_monitor_diagnostic_setting" "aks" {
  name               = "aks-diagnostic-setting"
  target_resource_id = azurerm_kubernetes_cluster.demo.id

  eventhub_name                  = azurerm_eventhub.diagnostic.name
  eventhub_authorization_rule_id = azurerm_eventhub_namespace_authorization_rule.monitor.id

  dynamic "enabled_log" {
    for_each = data.azurerm_monitor_diagnostic_categories.aks.log_category_types
    content {
      category = enabled_log.value
    }
  }

  dynamic "metric" {
    for_each = data.azurerm_monitor_diagnostic_categories.aks.metrics
    content {
      category = metric.value
      enabled  = true
    }
  }
}