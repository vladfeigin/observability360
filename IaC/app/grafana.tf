locals {
  grafana_image_name     = "${var.base_name}-grafana:latest"
  grafana_directory_path = "../../grafana"
}

resource "time_rotating" "example" {
  rotation_days = 180
}

resource "azuread_application" "grafana_to_adx" {
  display_name = "grafana_to_adx"
  owners       = [data.azuread_client_config.current.object_id]

  password {
    display_name = "${var.base_name}-secret"
    start_date   = time_rotating.example.id
    end_date     = timeadd(time_rotating.example.id, "4320h")
  }
}

resource "azuread_service_principal" "grafana_to_adx" {
  client_id                    = azuread_application.grafana_to_adx.client_id
  app_role_assignment_required = false
  owners                       = [data.azuread_client_config.current.object_id]
}

resource "azurerm_kusto_database_principal_assignment" "grafana_to_adx" {
  count = var.is_fabric ? 0 : 1

  name                = "GrafanaQueryToADX"
  resource_group_name = data.azurerm_resource_group.demo.name
  cluster_name        = data.azurerm_kusto_cluster.demo[0].name
  database_name       = data.azurerm_kusto_database.otel[0].name

  tenant_id      = data.azuread_client_config.current.tenant_id
  principal_id   = azuread_application.grafana_to_adx.client_id
  principal_type = "App"
  role           = "Viewer"
}

resource "azurerm_role_assignment" "grafana_to_communication_service" {
  scope                = azurerm_communication_service.demo.id
  role_definition_name = azurerm_role_definition.communication_service_role.name
  principal_id         = azuread_service_principal.grafana_to_adx.object_id
  principal_type       = "ServicePrincipal"
}

resource "azuread_service_principal_password" "grafana_to_adx" {
  service_principal_id = azuread_service_principal.grafana_to_adx.id
  depends_on           = [azurerm_kusto_database_principal_assignment.grafana_to_adx, azurerm_role_assignment.grafana_to_communication_service]
}

resource "local_file" "adx_datasource" {
  filename = "${path.cwd}/${local.grafana_directory_path}/provisioning/datasources/adx-datasource.yml"
  content = templatefile("${path.cwd}/${local.grafana_directory_path}/provisioning/datasources/adx-datasource.yml.tftpl", {
    adx_fqdn              = var.is_fabric ? data.fabric_kql_database.demo[0].properties.query_service_uri : data.azurerm_kusto_cluster.demo[0].uri
    adx_database          = "observabilitydb"
    grafana_client_id     = azuread_application.grafana_to_adx.client_id
    grafana_client_secret = azuread_service_principal_password.grafana_to_adx.value
    tenant_id             = data.azuread_client_config.current.tenant_id
  })
}

resource "local_file" "grafana_ini" {
  filename = "${path.cwd}/${local.grafana_directory_path}/grafana.ini"
  content = templatefile("${path.cwd}/${local.grafana_directory_path}/grafana.ini.tftpl", {
    user         = "${azurerm_communication_service.demo.name}|${azuread_application.grafana_to_adx.client_id}|${data.azuread_client_config.current.tenant_id}"
    password     = tolist(azuread_application.grafana_to_adx.password).0.value
    from_address = azurerm_email_communication_service_domain.demo.mail_from_sender_domain
  })
}

resource "local_file" "contact_group" {
  filename = "${path.cwd}/${local.grafana_directory_path}/provisioning/alerting/contact_group.yml"
  content = templatefile("${path.cwd}/${local.grafana_directory_path}/provisioning/alerting/contact_group.yml.tftpl", {
    email = var.email
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

  depends_on = [local_file.adx_datasource, local_file.grafana_ini]
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