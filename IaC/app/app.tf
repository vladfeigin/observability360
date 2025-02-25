locals {
  backend_image_name = "${var.base_name}-backend:latest"
  backend_directory_path = "../../python-app"
}

resource "docker_image" "backend" {
  name = "${data.azurerm_container_registry.demo.login_server}/${local.backend_image_name}"
  keep_locally = false
  
  build {
    context = "${path.cwd}/${local.backend_directory_path}"
  }

  triggers = {
    dir_sha1 = sha1(join("", [for f in fileset(path.cwd, "${local.backend_directory_path}/*") : filesha1(f)]))
  }
}

resource "docker_registry_image" "backend" {
  name          = docker_image.backend.name
  keep_remotely = true

  triggers = {
    dir_sha1 = sha1(join("", [for f in fileset(path.cwd, "${local.backend_directory_path}/*")  : filesha1(f)]))
  } 
}

resource "azurerm_container_app" "backend" {
  name                         = "backend"
  container_app_environment_id = data.azurerm_container_app_environment.demo.id
  resource_group_name          = data.azurerm_resource_group.demo.name
  revision_mode                = "Single"

  template {
    min_replicas = 1
    max_replicas = 3

    container {
      name   = "backend"
      image  = docker_image.backend.name
      cpu    = 1
      memory = "2Gi"
      
      env {
        name = "OTEL_SERVICE_NAME"
        value = "python-service"
      }
      
      env {
        name = "OTEL_EXPORTER_OTLP_ENDPOINT"
        value = "http://${azurerm_container_group.otel_collector.fqdn}:4317"
      }
      
      env {
        name = "OTEL_PYTHON_LOG_CORRELATION"
        value = "true"
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
    target_port = 8000
    traffic_weight {
      percentage = 100
      latest_revision = true
    }
  }

  depends_on = [ docker_registry_image.backend ]
}