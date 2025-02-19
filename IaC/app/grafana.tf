locals {
  grafana_image_name = "${var.base_name}-grafana:latest"
  grafana_directory_path = "../../grafana"
  
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