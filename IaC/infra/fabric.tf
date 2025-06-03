data "azuread_user" "current" {
  count = var.is_fabric ? 1 : 0

  object_id = data.azurerm_client_config.current.object_id
}

resource "azurerm_fabric_capacity" "demo" {
  count = var.is_fabric ? 1 : 0

  name                = "${var.base_name}capacity"
  location            = var.region
  resource_group_name = azurerm_resource_group.demo.name

  administration_members = [data.azuread_user.current[0].user_principal_name]

  sku {
    name = var.fabric_capacity_sku
    tier = "Fabric"
  }
}

data "fabric_capacity" "demo" {
  count = var.is_fabric ? 1 : 0

  display_name = azurerm_fabric_capacity.demo[0].name

  lifecycle {
    postcondition {
      condition     = self.state == "Active"
      error_message = "Fabric Capacity is not in Active state. Please check the Fabric Capacity status."
    }
  }
}

resource "fabric_workspace" "demo" {
  count = var.is_fabric ? 1 : 0

  display_name = "${var.base_name}-workspace"
  description  = "Workspace for Observability360 demo"
  capacity_id  = data.fabric_capacity.demo[0].id
  identity = {
    type = "SystemAssigned"
  }
}

resource "fabric_eventhouse" "demo" {
  count = var.is_fabric ? 1 : 0

  display_name = "${var.base_name}-eventhouse"
  workspace_id = fabric_workspace.demo[0].id

  configuration = {
    minimum_consumption_units = "2.25"
  }
}

resource "fabric_kql_database" "demo" {
  count = var.is_fabric ? 1 : 0

  display_name = "${var.base_name}-kql-database"
  workspace_id = fabric_workspace.demo[0].id

  configuration = {
    database_type = "ReadWrite"
    eventhouse_id = fabric_eventhouse.demo[0].id
  }
}

resource "fabric_eventstream" "diagnostics" {
  count = var.is_fabric ? 1 : 0

  display_name = "diagnostics-eventstream"
  workspace_id = fabric_workspace.demo[0].id
}

resource "fabric_eventstream" "operational" {
  count = var.is_fabric ? 1 : 0

  display_name = "operational-eventstream"
  workspace_id = fabric_workspace.demo[0].id
}