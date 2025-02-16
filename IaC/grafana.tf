locals {
  grafana_image_name = "${var.base_name}-grafana:latest"
}

resource "docker_image" "grafana" {
  name = "${azurerm_container_registry.demo.login_server}/${local.grafana_image_name}"
  keep_locally = false
  
  build {
    context = "${path.cwd}/grafana"
  }

  triggers = {
    dir_sha1 = sha1(join("", [for f in fileset(path.cwd, "grafana/*") : filesha1(f)]))
  }
}

resource "docker_registry_image" "grafana" {
  name          = docker_image.grafana.name
  keep_remotely = true

  triggers = {
    dir_sha1 = sha1(join("", [for f in fileset(path.cwd, "grafana/*") : filesha1(f)]))
  } 
  
}

resource "azurerm_linux_web_app" "grafana" {
  name                = "${var.base_name}-grafana-web-app"
  location            = var.region
  resource_group_name = azurerm_resource_group.demo.name
  service_plan_id     = azurerm_service_plan.demo.id

  


  site_config {
    always_on = true
    application_stack {
        docker_registry_url = "https://${azurerm_container_registry.demo.login_server}"
        docker_image_name = "${var.base_name}-grafana:latest"
        docker_registry_username = azurerm_container_registry.demo.admin_username
        docker_registry_password = azurerm_container_registry.demo.admin_password
    }
  }

  depends_on = [ docker_registry_image.grafana ]
}