locals {
  grafana_image_name     = "${var.base_name}-grafana:latest"
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

  depends_on = [azuread_service_principal_password.grafana_to_adx]
}

resource "local_file" "adx_datasource" {
  filename = "${path.cwd}/${local.grafana_directory_path}/provisioning/datasources/adx-datasource.yml"
  content = templatefile("${path.cwd}/${local.grafana_directory_path}/provisioning/datasources/adx-datasource.yml.tftpl", {
    adx_fqdn              = data.azurerm_kusto_cluster.demo.uri
    adx_database          = data.azurerm_kusto_database.otel.name
    grafana_client_id     = azuread_application.grafana_to_adx.client_id
    grafana_client_secret = azuread_service_principal_password.grafana_to_adx.value
    tenant_id             = data.azuread_client_config.current.tenant_id
  })
}

resource "docker_image" "grafana" {
  name         = "${data.azurerm_container_registry.demo.login_server}/${local.grafana_image_name}"
  keep_locally = false

  build {
    context  = "${path.cwd}/${local.grafana_directory_path}"
    platform = "linux/amd64"
  }

  triggers = {
    dir_sha1 = sha1(join("", [for f in fileset(path.cwd, "${local.grafana_directory_path}/**") : filesha1(f)]))
  }

  depends_on = [local_file.adx_datasource]
}

resource "docker_registry_image" "grafana" {
  name          = docker_image.grafana.name
  keep_remotely = true

  triggers = {
    dir_sha1 = sha1(join("", [for f in fileset(path.cwd, "${local.grafana_directory_path}/**") : filesha1(f)]))
  }
  depends_on = [docker_image.grafana]
}

resource "kubernetes_namespace" "grafana" {
  metadata {
    name = "grafana"
  }
}

resource "kubernetes_deployment" "grafana" {
  metadata {
    name      = "grafana"
    namespace = kubernetes_namespace.grafana.metadata[0].name
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = "grafana"
      }
    }

    template {
      metadata {
        labels = {
          app = "grafana"
        }
      }

      spec {
        container {
          name  = "grafana"
          image = docker_registry_image.grafana.name

          port {
            container_port = 3000
          }

          env {
            name  = "GF_INSTALL_PLUGINS"
            value = "grafana-opensearch-datasource,grafana-azure-data-explorer-datasource"
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "grafana" {
  metadata {
    name      = "grafana"
    namespace = kubernetes_namespace.grafana.metadata[0].name
  }

  spec {
    selector = {
      app = "grafana"
    }

    port {
      port        = 80
      target_port = 3000
    }
    type = "LoadBalancer"
  }
}