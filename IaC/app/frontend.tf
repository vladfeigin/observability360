# locals {
#   frontend_image_name = "${var.base_name}-frontend:latest"
#   frontend_directory_path = "../../application/frontend"
# }


# resource "local_file" "frontend_env" {
#   filename = "${path.cwd}/${local.frontend_directory_path}/Dockerfile"
#   content = templatefile("${path.cwd}/${local.frontend_directory_path}/Dockerfile.tftpl", {
#     adx_fqdn = data.azurerm_kusto_cluster.demo.uri
#   })
# }

# resource "docker_image" "frontend" {
#   name = "${data.azurerm_container_registry.demo.login_server}/${local.frontend_image_name}"
#   keep_locally = false

#   build {
#     context = "${path.cwd}/${local.frontend_directory_path}"
#   }

#   triggers = {
#     dir_sha1 = sha1(join("", [for f in fileset(path.cwd, "${local.frontend_directory_path}/**") : filesha1(f)]))
#   }

#   depends_on = [ local_file.frontend_env ]
# }

# resource "docker_registry_image" "frontend" {
#   name          = docker_image.frontend.name
#   keep_remotely = true

#   triggers = {
#     dir_sha1 = sha1(join("", [for f in fileset(path.cwd, "${local.frontend_directory_path}/**")  : filesha1(f)]))
#   } 
# }

# resource "azurerm_container_app" "frontend" {
#   name                         = "frontend"
#   container_app_environment_id = data.azurerm_container_app_environment.demo.id
#   resource_group_name          = data.azurerm_resource_group.demo.name
#   revision_mode                = "Single"

#   template {
#     min_replicas = 1
#     max_replicas = 3

#     container {
#       name   = "frontend"
#       image  = docker_image.frontend.name
#       cpu    = 1
#       memory = "2Gi"

#       env {
#         name = "OTEL_SERVICE_NAME"
#         value = "frontend-service"
#       }

#       env {
#         name = "OTEL_EXPORTER_OTLP_ENDPOINT"
#         value = "http://${azurerm_container_group.otel_collector.fqdn}:4318/v1/logs"
#       }
#     }
#   }

#   secret {
#     name = "acr-password"
#     value = data.azurerm_container_registry.demo.admin_password
#   }

#   registry {
#     server = data.azurerm_container_registry.demo.login_server
#     username = data.azurerm_container_registry.demo.admin_username
#     password_secret_name =  "acr-password"

#   }

#   ingress {
#     external_enabled = true
#     allow_insecure_connections = true
#     target_port = 3000
#     traffic_weight {
#       percentage = 100
#       latest_revision = true
#     }
#   }

#   depends_on = [ docker_registry_image.frontend ]
# }