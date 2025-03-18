resource "azurerm_container_registry" "demo" {
  name                = "${var.base_name}acr"
  location            = var.region
  resource_group_name = azurerm_resource_group.demo.name
  sku                 = "Basic"
  admin_enabled       = true
}

# Monitoring
data "azurerm_monitor_diagnostic_categories" "acr" {
  resource_id = azurerm_container_registry.demo.id
}

resource "azurerm_monitor_diagnostic_setting" "acr_logs" {
  name               = "acr-logs-diagnostic-setting"
  target_resource_id = azurerm_container_registry.demo.id

  eventhub_name                  = azurerm_eventhub.logs.name
  eventhub_authorization_rule_id = azurerm_eventhub_namespace_authorization_rule.monitor.id

  dynamic "enabled_log" {
    for_each = data.azurerm_monitor_diagnostic_categories.acr.log_category_types
    content {
      category = enabled_log.value
    }
  }

  lifecycle {
    ignore_changes = [metric]
  }
}

resource "azurerm_monitor_diagnostic_setting" "acr_metrics" {
  name               = "acr-metrics-diagnostic-setting"
  target_resource_id = azurerm_container_registry.demo.id

  eventhub_name                  = azurerm_eventhub.metrics.name
  eventhub_authorization_rule_id = azurerm_eventhub_namespace_authorization_rule.monitor.id

  dynamic "metric" {
    for_each = data.azurerm_monitor_diagnostic_categories.acr.metrics
    content {
      category = metric.value
      enabled  = true
    }
  }
}