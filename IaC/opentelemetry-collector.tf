resource "azuread_application" "otel" {
  display_name = "otelcollector"
  owners       = [data.azuread_client_config.current.object_id]
}

resource "azuread_service_principal" "otel" {
  client_id                    = azuread_application.otel.client_id
  app_role_assignment_required = false
  owners                       = [data.azuread_client_config.current.object_id]
}

resource "azurerm_kusto_database_principal_assignment" "otel" {
  name                = "KustoPrincipalAssignment"
  resource_group_name = azurerm_resource_group.demo.name
  cluster_name        = azurerm_kusto_cluster.demo.name
  database_name       = azurerm_kusto_database.otel.name

  tenant_id      = data.azuread_client_config.current.tenant_id
  principal_id   = azuread_application.otel.client_id
  principal_type = "App"
  role           = "Ingestor"
}

resource "azuread_service_principal_password" "otel" {
  service_principal_id = azuread_service_principal.otel.id
}

locals {
  opentelemetry_collector_config_file_path = "${path.cwd}/../opentelemetry-collector/config"
}

resource "local_file" "otel_collector_config" {
  filename = "${local.opentelemetry_collector_config_file_path}.yaml"
  content = templatefile("${local.opentelemetry_collector_config_file_path}.tftpl", {
    adx_cluster_uri = azurerm_kusto_cluster.demo.uri,
    application_id = azuread_service_principal.otel.client_id,
    application_key = azuread_service_principal_password.otel.value,
    tenant_id = data.azuread_client_config.current.tenant_id
  })
}


locals {
  otel_collector_image_name = "${var.base_name}-otel-collector:latest"
}

resource "docker_image" "otel_collector" {
  name = "${azurerm_container_registry.demo.login_server}/${local.otel_collector_image_name}"
  keep_locally = false
  
  build {
    context = "${path.cwd}/../opentelemetry-collector"
  }

  triggers = {
    dir_sha1 = sha1(join("", [for f in fileset(path.cwd, "../opentelemetry-collector/*") : filesha1(f)]))
  }
}

resource "docker_registry_image" "otel_collector" {
  name          = docker_image.otel_collector.name
  keep_remotely = true

  triggers = {
    dir_sha1 = sha1(join("", [for f in fileset(path.cwd, "../opentelemetry-collector/*") : filesha1(f)]))
  } 
}

resource "azurerm_container_app_environment" "otel" {
  name                       = "Otel-Collector-Environment"
  location                   = var.region
  resource_group_name        = azurerm_resource_group.demo.name
}

resource "azurerm_container_app" "otel" {
  name                         = "otel-collector"
  container_app_environment_id = azurerm_container_app_environment.otel.id
  resource_group_name          = azurerm_resource_group.demo.name
  revision_mode                = "Single"

  template {
    container {
      name   = "otel-collector"
      image  = docker_image.otel_collector.name
      cpu    = 1
      memory = "2Gi"
    }
  }
  secret {
    name = "acr-password"
    value = azurerm_container_registry.demo.admin_password
  }

  registry {
    server = azurerm_container_registry.demo.login_server
    username = azurerm_container_registry.demo.admin_username
    password_secret_name =  "acr-password"
    
  }
  
  ingress {
    external_enabled = true
    allow_insecure_connections = true
    target_port = 4318
    # transport = "http2"
    traffic_weight {
      percentage = 100
      latest_revision = true
    }
  }

  depends_on = [ docker_registry_image.otel_collector ]
}


# resource "azurerm_linux_web_app" "otel_collector" {
#   name                = "${var.base_name}-otel-collector-web-app"
#   location            = var.region
#   resource_group_name = azurerm_resource_group.demo.name
#   service_plan_id     = azurerm_service_plan.demo.id

#   site_config {
#     always_on = true
#     application_stack {
#         docker_registry_url = "https://${azurerm_container_registry.demo.login_server}"
#         docker_image_name = local.otel_collector_image_name
#         docker_registry_username = azurerm_container_registry.demo.admin_username
#         docker_registry_password = azurerm_container_registry.demo.admin_password
#     }
#   }

#   depends_on = [ docker_registry_image.otel_collector ]
# }