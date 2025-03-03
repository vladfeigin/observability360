locals {
  aks_name = "${var.base_name}-aks"
}

# AGIC Ingress Controller

locals {
  backend_address_pool_name      = "${azurerm_virtual_network.demo.name}-beap"
  frontend_port_name             = "${azurerm_virtual_network.demo.name}-feport"
  frontend_ip_configuration_name = "${azurerm_virtual_network.demo.name}-feip"
  http_setting_name              = "${azurerm_virtual_network.demo.name}-be-htst"
  listener_name                  = "${azurerm_virtual_network.demo.name}-httplstn"
  request_routing_rule_name      = "${azurerm_virtual_network.demo.name}-rqrt"
}

resource "azurerm_public_ip" "appgw_pip" {
  name                = "appgw-pip"
  resource_group_name = azurerm_resource_group.demo.name
  location            = var.region
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_application_gateway" "aks" {
  name                = "${local.aks_name}-appgw"
  resource_group_name = azurerm_resource_group.demo.name
  location            = azurerm_resource_group.demo.location

  sku {
    name     = "Standard_v2"
    tier     = "Standard_v2"
    capacity = 1
  }

  gateway_ip_configuration {
    name      = "appGatewayIpConfig"
    subnet_id = azurerm_subnet.appgw.id
  }

  frontend_port {
    name = local.frontend_port_name
    port = 80
  }

  frontend_ip_configuration {
    name                 = local.frontend_ip_configuration_name
    public_ip_address_id = azurerm_public_ip.appgw_pip.id
  }

  backend_address_pool {
    name = local.backend_address_pool_name
  }

  backend_http_settings {
    name                  = local.http_setting_name
    cookie_based_affinity = "Disabled"
    port                  = 80
    protocol              = "Http"
    request_timeout       = 1
  }

  http_listener {
    name                           = local.listener_name
    frontend_ip_configuration_name = local.frontend_ip_configuration_name
    frontend_port_name             = local.frontend_port_name
    protocol                       = "Http"
  }

  request_routing_rule {
    name                       = local.request_routing_rule_name
    priority                   = 1
    rule_type                  = "Basic"
    http_listener_name         = local.listener_name
    backend_address_pool_name  = local.backend_address_pool_name
    backend_http_settings_name = local.http_setting_name
  }

  lifecycle {
    ignore_changes = [
      tags,
      backend_address_pool,
      backend_http_settings,
      http_listener,
      probe,
      request_routing_rule,
    ]
  }
}

# AKS
resource "azurerm_user_assigned_identity" "aks" {
  name                = "${local.aks_name}-identity"
  resource_group_name = azurerm_resource_group.demo.name
  location            = var.region
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
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.aks.id]
  }

  network_profile {
    network_plugin = "azure"
    dns_service_ip = var.aks_dns_service_ip
    service_cidr   = var.aks_service_cidr
  }

  ingress_application_gateway {
    gateway_id = azurerm_application_gateway.aks.id
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

# AGIC Identity
 resource "azurerm_role_assignment" "reader" {
   scope                = azurerm_resource_group.demo.id
   role_definition_name = "Reader"
   principal_id         = azurerm_kubernetes_cluster.demo.ingress_application_gateway[0].ingress_application_gateway_identity[0].object_id
 }

 resource "azurerm_role_assignment" "network_contributor" {
   scope                = azurerm_virtual_network.demo.id
   role_definition_name = "Network Contributor"
   principal_id         = azurerm_kubernetes_cluster.demo.ingress_application_gateway[0].ingress_application_gateway_identity[0].object_id
 }

 resource "azurerm_role_assignment" "conributor" {
   scope                = azurerm_application_gateway.aks.id
   role_definition_name = "Contributor"
   principal_id         = azurerm_kubernetes_cluster.demo.ingress_application_gateway[0].ingress_application_gateway_identity[0].object_id
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
  min_count            = 1
  max_count            = 3
  vnet_subnet_id       = azurerm_subnet.aks.id

  node_labels = {
    environment = "workloadpool"
  }

  lifecycle {
    ignore_changes = [node_count]
  }
}