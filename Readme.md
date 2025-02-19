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
git clone https://github.com/vladfeigin/openteldemo.git
cd openteldemo
```

### 2. Deploy the demo services
Switch directory to the IaC directory using: ```cd IaC```.

Create a file named ```terraform.tfvars``` with the following content:

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
terraform apply -auto-approve -var-file="../terraform.tfvars"
```
wait for the process to finish, it might take a while.


#### 2.2. Deploy the application resources
make sure that docker runtime is running (Docker-Desktop for windows/mac and docker-ce for ubuntu)

```sh
cd ../app
terraform apply -auto-approve -var-file="../terraform.tfvars"
```

### 3. Create Tables in Azure Data Explorer

navigate into the created resource group in the portal and choose the created Azure Data Explorer, then run the following query on the database named ```openteldb```:
```kusto
.create-merge table OTELLogs (Timestamp:datetime, ObservedTimestamp:datetime, TraceID:string, SpanID:string, SeverityText:string, SeverityNumber:int, Body:string, ResourceAttributes:dynamic, LogsAttributes:dynamic) 

.create-merge table OTELMetrics (Timestamp:datetime, MetricName:string, MetricType:string, MetricUnit:string, MetricDescription:string, MetricValue:real, Host:string, ResourceAttributes:dynamic, MetricAttributes:dynamic) 

.create-merge table OTELTraces (TraceID:string, SpanID:string, ParentID:string, SpanName:string, SpanStatus:string, SpanKind:string, StartTime:datetime, EndTime:datetime, ResourceAttributes:dynamic, TraceAttributes:dynamic, Events:dynamic, Links:dynamic)
```

### 4. Validate functionallity
Navigate to the backend container app in the created resource group and copy it FQDN,

Preform a Get request to the following url: ```<BACKEND_FQDN>/process```

this operation will create a trace that will be navigated to the otel-collector which will insert it to the OTELTraces table.

Preform the following query in the ```openteldb``` database:

```
OTELTraces | take 100
```
and see the traces data (it might take few minutes)

### 5. Cleaning Up
To destroy the infrastructure and application, run each time in each directory, first the app directory:
```sh
terraform destroy -auto-approve
```

### 6. Contact
For any questions or feedback, please open an issue or contact the maintainers:

Vlad Feigin - vladfeigin@microsoft.com, Omer Feldman - omerfeldman@microsoft.com 
