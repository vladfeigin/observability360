resource "azurerm_kusto_cluster" "demo" {
  count = var.is_fabric ? 0 : 1

  name                = "${var.base_name}-adx"
  location            = var.region
  resource_group_name = azurerm_resource_group.demo.name

  sku {
    name     = var.adx_sku
    capacity = 2
  }
}

resource "azurerm_kusto_database" "observability" {
  count = var.is_fabric ? 0 : 1

  name                = "observabilitydb"
  resource_group_name = azurerm_resource_group.demo.name
  location            = var.region
  cluster_name        = azurerm_kusto_cluster.demo[0].name
}

resource "azurerm_kusto_script" "baseconfig" {
  count = var.is_fabric ? 0 : 1
  
  name                               = "baseconfig"
  database_id                        = azurerm_kusto_database.observability[0].id
  continue_on_errors_enabled         = true
  force_an_update_when_value_changed = "first"
  script_content = <<EOT
.create-merge table OTELLogs (Timestamp:datetime, ObservedTimestamp:datetime, TraceID:string, SpanID:string, SeverityText:string, SeverityNumber:int, Body:string, ResourceAttributes:dynamic, LogsAttributes:dynamic) 
.create-merge table OTELMetrics (Timestamp:datetime, MetricName:string, MetricType:string, MetricUnit:string, MetricDescription:string, MetricValue:real, Host:string, ResourceAttributes:dynamic, MetricAttributes:dynamic) 
.create-merge table OTELTraces (TraceID:string, SpanID:string, ParentID:string, SpanName:string, SpanStatus:string, SpanKind:string, StartTime:datetime, EndTime:datetime, ResourceAttributes:dynamic, TraceAttributes:dynamic, Events:dynamic, Links:dynamic)
.create table DiagnosticLogs (Timestamp:datetime, ResourceId:string, OperationName:string, Result:string, OperationId:string, Database:string, Table:string, IngestionSourceId:string, IngestionSourcePath:string, RootActivityId:string, ErrorCode:string, FailureStatus:string, Details:string)
.create table DiagnosticMetrics (Timestamp:datetime, ResourceId:string, MetricName:string, Count:int, Total:double, Minimum:double, Maximum:double, Average:double, TimeGrain:string)
.create table DiagnosticRawRecords (Records:dynamic)
.alter-merge table DiagnosticRawRecords policy retention softdelete = 0d
.create table ActivityLogs (Timestamp:datetime, ResourceId:string, OperationName:string, Category:string, ResultType:string, ResultSignature:string, DurationMs:int, IdentityAuthorization:dynamic, IdentityClaims:dynamic, Location:string, Level:string)
.create table ActivityLogsRawRecords (Records:dynamic)
.alter-merge table ActivityLogsRawRecords policy retention softdelete = 0d
.create table DiagnosticRawRecords ingestion json mapping 'DiagnosticRawRecordsMapping' '[{"column":"Records","Properties":{"path":"$.records"}}]'
.create table ActivityLogsRawRecords ingestion json mapping 'ActivityLogsRawRecordsMapping' '[{"column":"Records","Properties":{"path":"$.records"}}]'
.create function DiagnosticMetricsExpand() {
   DiagnosticRawRecords
   | mv-expand events = Records
   | where isnotempty(events.metricName)
   | project
       Timestamp = todatetime(events['time']),
       ResourceId = tostring(events.resourceId),
       MetricName = tostring(events.metricName),
       Count = toint(events['count']),
       Total = todouble(events.total),
       Minimum = todouble(events.minimum),
       Maximum = todouble(events.maximum),
       Average = todouble(events.average),
       TimeGrain = tostring(events.timeGrain)
}
.alter table DiagnosticMetrics policy update @'[{"Source": "DiagnosticRawRecords", "Query": "DiagnosticMetricsExpand()", "IsEnabled": "True", "IsTransactional": true}]'
.create function DiagnosticLogsExpand() {
    DiagnosticRawRecords
    | mv-expand events = Records
    | where isnotempty(events.operationName)
    | project
        Timestamp = todatetime(events['time']),
        ResourceId = tostring(events.resourceId),
        OperationName = tostring(events.operationName),
        Result = tostring(events.resultType),
        OperationId = tostring(events.properties.OperationId),
        Database = tostring(events.properties.Database),
        Table = tostring(events.properties.Table),
        IngestionSourceId = tostring(events.properties.IngestionSourceId),
        IngestionSourcePath = tostring(events.properties.IngestionSourcePath),
        RootActivityId = tostring(events.properties.RootActivityId),
        ErrorCode = tostring(events.properties.ErrorCode),
        FailureStatus = tostring(events.properties.FailureStatus),
        Details = tostring(events.properties.Details)
}
.alter table DiagnosticLogs policy update @'[{"Source": "DiagnosticRawRecords", "Query": "DiagnosticLogsExpand()", "IsEnabled": "True", "IsTransactional": true}]'
.create function ActivityLogRecordsExpand() {
    ActivityLogsRawRecords
    | mv-expand events = Records
    | project
        Timestamp = todatetime(events['time']),
        ResourceId = tostring(events.resourceId),
        OperationName = tostring(events.operationName),
        Category = tostring(events.category),
        ResultType = tostring(events.resultType),
        ResultSignature = tostring(events.resultSignature),
        DurationMs = toint(events.durationMs),
        IdentityAuthorization = events.identity.authorization,
        IdentityClaims = events.identity.claims,
        Location = tostring(events.location),
        Level = tostring(events.level)
}
.alter table ActivityLogs policy update @'[{"Source": "ActivityLogsRawRecords", "Query": "ActivityLogRecordsExpand()", "IsEnabled": "True", "IsTransactional": true}]'
EOT
}

# Monitoring
data "azurerm_monitor_diagnostic_categories" "adx" {
  count = var.is_fabric ? 0 : 1

  resource_id = azurerm_kusto_cluster.demo[0].id
}

resource "azurerm_monitor_diagnostic_setting" "adx" {
  count = var.is_fabric ? 0 : 1

  name               = "adx-diagnostic-setting"
  target_resource_id = azurerm_kusto_cluster.demo[0].id

  eventhub_name                  = azurerm_eventhub.diagnostic.name
  eventhub_authorization_rule_id = azurerm_eventhub_namespace_authorization_rule.monitor.id

  dynamic "enabled_log" {
    for_each = data.azurerm_monitor_diagnostic_categories.adx[0].log_category_types
    content {
      category = enabled_log.value
    }
  }

  dynamic "metric" {
    for_each = data.azurerm_monitor_diagnostic_categories.adx[0].metrics
    content {
      category = metric.value
      enabled  = true
    }
  }
}