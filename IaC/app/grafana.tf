locals {
  grafana_image_name = "${var.base_name}-grafana:latest"
  grafana_directory_path = "../../grafana"
  
}

resource "azuread_application" "grafana_to_adx" {
  display_name = "grafana_to_adx"
  owners       = [data.azuread_client_config.current.object_id]
}

resource "azuread_service_principal" "grafana_to_adx" {
  client_id                    = azuread_application.grafana_to_adx.client_id
  app_role_assignment_required = false
  owners                       = [data.azuread_client_config.current.object_id]
}

resource "azuread_service_principal_password" "grafana_to_adx" {
  service_principal_id = azuread_service_principal.grafana_to_adx.id
}

resource "azurerm_kusto_database_principal_assignment" "grafana_to_adx" {
  name                = "GrafanaQueryToADX"
  resource_group_name = data.azurerm_resource_group.demo.name
  cluster_name        = data.azurerm_kusto_cluster.demo.name
  database_name       = data.azurerm_kusto_database.otel.name

  tenant_id      = data.azuread_client_config.current.tenant_id
  principal_id   = azuread_application.grafana_to_adx.client_id
  principal_type = "App"
  role           = "Viewer"

  depends_on = [ azuread_service_principal_password.grafana_to_adx ]
}


resource "local_file" "adx_datasource" {
  filename = "${path.cwd}/${local.grafana_directory_path}/provisioning/datasources/adx-datasource.yml"
  content = templatefile("${path.cwd}/${local.grafana_directory_path}/provisioning/datasources/adx-datasource.yml.tftpl", {
    adx_fqdn = data.azurerm_kusto_cluster.demo.uri
    adx_database = data.azurerm_kusto_database.otel.name
    grafana_client_id = azuread_application.grafana_to_adx.client_id
    grafana_client_secret = azuread_service_principal_password.grafana_to_adx.value
    tenant_id = data.azuread_client_config.current.tenant_id
  })
}

resource "docker_image" "grafana" {
  name = "${data.azurerm_container_registry.demo.login_server}/${local.grafana_image_name}"
  keep_locally = false
  
  build {
    context = "${path.cwd}/${local.grafana_directory_path}"
  }

  triggers = {
    dir_sha1 = sha1(join("", [for f in fileset(path.cwd, "${local.grafana_directory_path}/*") : filesha1(f)]))
  }

  depends_on = [ local_file.adx_datasource ]
}

resource "docker_registry_image" "grafana" {
  name          = docker_image.grafana.name
  keep_remotely = true

  triggers = {
    dir_sha1 = sha1(join("", [for f in fileset(path.cwd, "${local.grafana_directory_path}/*") : filesha1(f)]))
  } 
}

resource "azurerm_container_app" "grafana" {
  name                         = "grafana"
  container_app_environment_id = data.azurerm_container_app_environment.demo.id
  resource_group_name          = data.azurerm_resource_group.demo.name
  revision_mode                = "Single"

  template {
    min_replicas = 1
    max_replicas = 3
    
    container {
      name   = "grafana"
      image  = docker_image.grafana.name
      cpu    = 1
      memory = "2Gi"

      env {
        name = "GF_INSTALL_PLUGINS"
        value = "grafana-opensearch-datasource,grafana-azure-data-explorer-datasource"
      }
    }
  }
  secret {
    name = "acr-password"
    value = data.azurerm_container_registry.demo.admin_password
  }

  registry {
    server = data.azurerm_container_registry.demo.login_server
    username = data.azurerm_container_registry.demo.admin_username
    password_secret_name =  "acr-password"
    
  }
  
  ingress {
    external_enabled = true
    allow_insecure_connections = true
    target_port = 3000
    traffic_weight {
      percentage = 100
      latest_revision = true
    }
  }

  depends_on = [ docker_registry_image.grafana ]
}