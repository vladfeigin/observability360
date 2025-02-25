locals {
  jaeger_directory_path = "../../jaeger"

  jaeger_plugin_directory_path = "${local.jaeger_directory_path}/plugin"
  jaeger_kusto_plugin_image_name = "${var.base_name}-jaeger-kusto-plugin:latest" 

  jaeger_kusto_plugin_dns_label = "${var.base_name}-jaeger-plugin"
  jaeger_kusto_plugin_fqdn = "${local.jaeger_kusto_plugin_dns_label}.${var.region}.azurecontainer.io"

  jaeger_dns_label = "${var.base_name}-jaeger"
  jaeger_fqdn = "${local.jaeger_dns_label}.${var.region}.azurecontainer.io"
  jaeger_image_name = "jaegertracing/all-in-one:1.55"
}

resource "azuread_application" "jaeger" {
  display_name = "jaeger"
  owners       = [data.azuread_client_config.current.object_id]
}

resource "azuread_service_principal" "jaeger" {
  client_id                    = azuread_application.jaeger.client_id
  app_role_assignment_required = false
  owners                       = [data.azuread_client_config.current.object_id]
}

resource "azuread_service_principal_password" "jaeger" {
  service_principal_id = azuread_service_principal.jaeger.id
}

resource "azurerm_kusto_database_principal_assignment" "jaeger" {
  name                = "KustoJaegerPrincipalAssignment"
  resource_group_name = data.azurerm_resource_group.demo.name
  cluster_name        = data.azurerm_kusto_cluster.demo.name
  database_name       = data.azurerm_kusto_database.otel.name

  tenant_id      = data.azuread_client_config.current.tenant_id
  principal_id   = azuread_application.jaeger.client_id
  principal_type = "App"
  role           = "Viewer"

  depends_on = [ azuread_service_principal_password.jaeger ]
}

resource "local_file" "jaeger_kusto_config" {
  filename = "${path.cwd}/${local.jaeger_plugin_directory_path}/jaeger-kusto-config.json"
  content = templatefile("${path.cwd}/${local.jaeger_plugin_directory_path}/jaeger-kusto-config.json.tftpl", {
    adx_cluster_uri = data.azurerm_kusto_cluster.demo.uri,
    adx_database = data.azurerm_kusto_database.otel.name,
    application_id = azuread_service_principal.jaeger.client_id,
    application_key = azuread_service_principal_password.jaeger.value,
    tenant_id = data.azuread_client_config.current.tenant_id
  })
}

resource "docker_image" "jaeger_plugin" {
  name = "${data.azurerm_container_registry.demo.login_server}/${local.jaeger_kusto_plugin_image_name}"
  keep_locally = false
  
  build {
    context = "${path.cwd}/${local.jaeger_plugin_directory_path}"
  }

  triggers = {
    dir_sha1 = sha1(join("", [for f in fileset(path.cwd, "${local.jaeger_plugin_directory_path}/**") : filesha1(f)]))
  }
  depends_on = [ local_file.jaeger_kusto_config ]
}

resource "docker_registry_image" "jaeger_plugin" {
  name          = docker_image.jaeger_plugin.name
  keep_remotely = true

  triggers = {
    dir_sha1 = sha1(join("", [for f in fileset(path.cwd, "${local.jaeger_plugin_directory_path}/**") : filesha1(f)]))
  } 
}


resource "azurerm_container_group" "jaeger_plugin" {
  name                = "jaeger-plugin"
  location            = data.azurerm_resource_group.demo.location
  resource_group_name = data.azurerm_resource_group.demo.name
  ip_address_type     = "Public"
  dns_name_label      = local.jaeger_kusto_plugin_dns_label
  os_type             = "Linux"

  image_registry_credential {
    server = data.azurerm_container_registry.demo.login_server
    username = data.azurerm_container_registry.demo.admin_username
    password = data.azurerm_container_registry.demo.admin_password
  }

  container {
    name   = "jaeger-plugin"
    image = docker_registry_image.jaeger_plugin.name
    cpu    = "1"
    memory = "2"

    ports {
      port     = 6060
      protocol = "TCP"
    }

    ports {
      port     = 8989
      protocol = "TCP"
    }

    environment_variables = {
        "JAEGER_AGENT_HOST": local.jaeger_fqdn, 
        "JAEGER_AGENT_PORT": "6831"
    }
  }

  depends_on = [ docker_registry_image.jaeger_plugin ]
}

resource "azurerm_container_group" "jaeger" {
  name                = "jaeger"
  location            = data.azurerm_resource_group.demo.location
  resource_group_name = data.azurerm_resource_group.demo.name
  ip_address_type     = "Public"
  dns_name_label      = local.jaeger_dns_label
  os_type             = "Linux"

  container {
    name   = "jaeger"
    image = "jaegertracing/all-in-one:1.55"
    cpu    = "4"
    memory = "8"

    ports {
      port     = 6831
      protocol = "UDP"
    }

    ports {
      port     = 6832
      protocol = "UDP"
    }

    ports {
      port     = 5778
      protocol = "TCP"
    }

    ports {
      port     = 16686
      protocol = "TCP"
    }

    ports {
      port     = 14268
      protocol = "TCP"
    }


    environment_variables = {
        "SPAN_STORAGE_TYPE" : "grpc-plugin",
        "GRPC_STORAGE_SERVER": "${local.jaeger_kusto_plugin_fqdn}:8989",
        "GRPC_STORAGE_CONNECTION_TIMEOUR": "60s",
        "GRPC_STORAGE_TLS_ENABLED": "false"
    }
  }

  depends_on = [ docker_registry_image.jaeger_plugin ]
}