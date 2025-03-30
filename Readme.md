# OpenTelemetry Demo

This repository contains a demo for deploying OpenTelemetry with Azure Data Explorer for observability. The demo includes setting up infrastructure and application components using Terraform.

## Prerequisites

Before you begin, ensure you have the following installed:

- [Terraform](https://www.terraform.io/downloads.html)
- [Docker](https://www.docker.com/get-started)
- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)

## Deployment Steps

### 1. Clone the Repository

```sh
git clone https://github.com/vladfeigin/observability360.git
cd observability360
```

### 2. Deploy the demo services

Switch directory to the IaC directory using: ``cd IaC``.

Create a file named ``terraform.tfvars`` with the following content:

```
subscription_id = "<your_subscription_id>"
base_name = "<base_name_prefix_for_the_created_resources>"
```

run az login in order to authenticate and authorize to azure:

```
az login
```

#### 2.1 deploy the infrastructure resources

```sh
cd infra
terraform init
terraform apply -auto-approve -var-file="../terraform.tfvars"
```

wait for the process to finish, it might take a while.

##### 2.1.1. Create Tables in Azure Data Explorer

navigate into the created resource group in the portal and choose the created Azure Data Explorer, then run the following query on the database named ``openteldb``:

```kusto
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


```

#### 2.2. Deploy the application resources

make sure that docker runtime is running (Docker-Desktop for windows/mac and docker-ce for ubuntu)

```sh
cd ../app
terraform init
terraform apply -auto-approve -var-file="../terraform.tfvars"
```
Note: If you get an error: 

`app folder :Error: Invalid function argument
│   on opentelemetry-collector.tf line 60, in resource "kubernetes_config_map" "collector_config":
│"config.yaml" = file(local_file.otel_collector_config.filename)
`

Run first this command:
```sh
terraform apply -auto-approve -var-file="../terraform.tfvars" -target=local_file.otel_collector_config
```

and after that run the command again:
```sh
terraform apply -auto-approve -var-file="../terraform.tfvars"
```

### 3. Validate functionallity

Navigate to the backend container app in the created resource group and copy it FQDN,

Preform a Get request to the following url: ``<BACKEND_FQDN>/process``

this operation will create a trace that will be navigated to the otel-collector which will insert it to the OTELTraces table.

Preform the following query in the ``openteldb`` database:

```
OTELTraces | take 100
```

and see the traces data (it might take few minutes)

### 4. Online Store

Online Store Application is a demo that simulates a complete online store. It functions as a target monitored application, providing essential services such as user management, product management, and order processing. This setup enables you to deploy and evaluate observability tools in a realistic environment.

## Online Store Services

The online store is composed of several services:
1. **User Service**  
    Manages online store user accounts.
    Located in the `online_store\user` directory.
    Operates on port 5000.
2. **Product Service**  
    Located in the `online_store/product` directory.  
    Manages product information and catalog data, ensuring the seamless handling of your inventory details.  
    Operates on port 5001.
3. **Cart Service**  
    Manages user shopping carts.
    Located in the `online_store\cart` directory.
    Operates on port 5002.
4. **Order Service**  
    Order processing.
    Located in the `online_store\order` directory.
    Operates on port 5003.
5. **Online Store UI**
    The online store UI.
    Located in the `online_store\ui` directory.
    Operates on port 8501.

The online store UI is built using [Streamlit](https://streamlit.io/). To launch it, run the following command from the project root:
    `streamlit run ./online_store/ui/online_store_ui.py`

The all services must be started from project root directory as:
    `python -m online_store.<service name>.app`
For example **user** service :
    `python -m online_store.user.app`

### 5. Cleaning Up

To destroy the infrastructure and application, run each time in each directory, first the app directory:

```sh
terraform destroy -auto-approve
```

### 6. Contact

For any questions or feedback, please open an issue or contact the maintainers:

Vlad Feigin - vladfeigin@microsoft.com, Omer Feldman - omerfeldman@microsoft.com
