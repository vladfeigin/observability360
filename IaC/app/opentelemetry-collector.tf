locals {
  otel_collector_image_name = "${var.base_name}-otel-collector:latest"
  opentelemetry_collector_directory_path = "../../opentelemetry-collector"
}

resource "azuread_application" "otel" {
  display_name = "otelcollector"
  owners       = [data.azuread_client_config.current.object_id]
}

resource "azuread_service_principal" "otel" {
  client_id                    = azuread_application.otel.client_id
  app_role_assignment_required = false
  owners                       = [data.azuread_client_config.current.object_id]
}

resource "azuread_service_principal_password" "otel" {
  service_principal_id = azuread_service_principal.otel.id
}

resource "azurerm_kusto_database_principal_assignment" "otel" {
  name                = "KustoPrincipalAssignment"
  resource_group_name = data.azurerm_resource_group.demo.name
  cluster_name        = data.azurerm_kusto_cluster.demo.name
  database_name       = data.azurerm_kusto_database.otel.name

  tenant_id      = data.azuread_client_config.current.tenant_id
  principal_id   = azuread_application.otel.client_id
  principal_type = "App"
  role           = "Ingestor"

  depends_on = [ azuread_service_principal_password.otel ]
}

resource "local_file" "otel_collector_config" {
  filename = "${path.cwd}/${local.opentelemetry_collector_directory_path}/config.yaml"
  content = templatefile("${path.cwd}/${local.opentelemetry_collector_directory_path}/config.tftpl", {
    adx_cluster_uri = data.azurerm_kusto_cluster.demo.uri,
    application_id = azuread_service_principal.otel.client_id,
    application_key = azuread_service_principal_password.otel.value,
    tenant_id = data.azuread_client_config.current.tenant_id
  })
}

resource "docker_image" "otel_collector" {
  name = "${data.azurerm_container_registry.demo.login_server}/${local.otel_collector_image_name}"
  keep_locally = false
  
  build {
    context = "${path.cwd}/${local.opentelemetry_collector_directory_path}"
  }

  triggers = {
    dir_sha1 = sha1(join("", [for f in fileset(path.cwd, "${local.opentelemetry_collector_directory_path}/*") : filesha1(f)]))
  }
  depends_on = [ local_file.otel_collector_config ]
}

resource "docker_registry_image" "otel_collector" {
  name          = docker_image.otel_collector.name
  keep_remotely = true

  triggers = {
    dir_sha1 = sha1(join("", [for f in fileset(path.cwd, "${local.opentelemetry_collector_directory_path}/*") : filesha1(f)]))
  } 
}

resource "azurerm_container_group" "otel_collector" {
  name                = "otel-collector"
  location            = data.azurerm_resource_group.demo.location
  resource_group_name = data.azurerm_resource_group.demo.name
  ip_address_type     = "Public"
  dns_name_label      = "${var.base_name}-otel-collector"
  os_type             = "Linux"

  image_registry_credential {
    server = data.azurerm_container_registry.demo.login_server
    username = data.azurerm_container_registry.demo.admin_username
    password = data.azurerm_container_registry.demo.admin_password
  }

  container {
    name   = "otel-collector"
    image = docker_registry_image.otel_collector.name
    cpu    = "1"
    memory = "2"

    ports {
      port     = 4317
      protocol = "TCP"
    }

    ports {
      port     = 4318
      protocol = "TCP"
    }
  }
}