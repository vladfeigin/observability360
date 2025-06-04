resource "azurerm_eventhub_namespace" "monitor" {
  name                = "${var.base_name}-monitor-eventhub"
  location            = var.region
  resource_group_name = azurerm_resource_group.demo.name
  sku                 = "Standard"
  capacity            = 1
}

resource "azurerm_eventhub" "diagnostic" {
  name              = "DiagnosticData"
  namespace_id      = azurerm_eventhub_namespace.monitor.id
  partition_count   = 2
  message_retention = 1
}

resource "azurerm_eventhub" "operational" {
  name              = "OperationalData"
  namespace_id      = azurerm_eventhub_namespace.monitor.id
  partition_count   = 2
  message_retention = 1
}

resource "azurerm_eventhub_consumer_group" "diagnostic" {
  name                = "KustoConsumerGroup"
  namespace_name      = azurerm_eventhub_namespace.monitor.name
  eventhub_name       = azurerm_eventhub.diagnostic.name
  resource_group_name = azurerm_resource_group.demo.name
}

resource "azurerm_eventhub_consumer_group" "operational" {
  name                = "KustoConsumerGroup"
  namespace_name      = azurerm_eventhub_namespace.monitor.name
  eventhub_name       = azurerm_eventhub.operational.name
  resource_group_name = azurerm_resource_group.demo.name
}

resource "azurerm_eventhub_namespace_authorization_rule" "monitor" {
  name                = "monitor-eventhub-auth"
  namespace_name      = azurerm_eventhub_namespace.monitor.name
  resource_group_name = azurerm_resource_group.demo.name

  listen = true
  send   = true
}

# Subscription level diagnostic setting for activity logs
resource "azurerm_monitor_diagnostic_setting" "subscription_activitylogs" {
  name               = "${var.base_name}-SubscriptionActivityLogs"
  target_resource_id = "/subscriptions/${var.subscription_id}"

  eventhub_name                  = azurerm_eventhub.operational.name
  eventhub_authorization_rule_id = azurerm_eventhub_namespace_authorization_rule.monitor.id


  dynamic "enabled_log" {
    iterator = entry
    for_each = ["Administrative", "Security", "ServiceHealth", "Alert", "Recommendation", "Policy", "Autoscale", "ResourceHealth"]
    content {
      category = entry.value
    }
  }
}