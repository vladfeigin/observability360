locals {
  online_store_ui_image_name     = "${local.online_store_docker_images_name_prefix}-ui:latest"
  online_store_ui_directory_name = "ui"
  online_store_ui_directory_path = "${local.online_store_directory_path}/${local.online_store_ui_directory_name}"
}


resource "docker_image" "online_store_ui" {
  name         = "${data.azurerm_container_registry.demo.login_server}/${local.online_store_ui_image_name}"
  keep_locally = false

  build {
    context    = "${path.cwd}/${local.online_store_directory_path}"
    dockerfile = "${local.online_store_ui_directory_name}/Dockerfile"
    platform   = "linux/amd64"
  }

  triggers = {
    dir_sha1      = sha1(join("", [for f in fileset(path.cwd, "${local.online_store_ui_directory_path}/*") : filesha1(f)]))
    dir_sha1_otel = sha1(join("", [for f in fileset(path.cwd, "${local.online_store_otel_directory_path}/*") : filesha1(f)]))
  }
}

resource "docker_registry_image" "online_store_ui" {
  name          = docker_image.online_store_ui.name
  keep_remotely = true

  triggers = {
    dir_sha1      = sha1(join("", [for f in fileset(path.cwd, "${local.online_store_ui_directory_path}/*") : filesha1(f)]))
    dir_sha1_otel = sha1(join("", [for f in fileset(path.cwd, "${local.online_store_otel_directory_path}/*") : filesha1(f)]))
  }
}


resource "kubernetes_deployment" "online_store_ui" {
  metadata {
    name      = "online-store-ui"
    namespace = kubernetes_namespace.online_store.metadata[0].name
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = "online-store-ui"
      }
    }

    template {
      metadata {
        labels = {
          app = "online-store-ui"
        }
      }

      spec {
        container {
          name  = "online-store-ui"
          image = docker_registry_image.online_store_ui.name
          resources {
            limits = {
              cpu    = "0.5"
              memory = "2Gi"
            }
            requests = {
              cpu    = "0.2"
              memory = "1Gi"
            }
          }

          port {
            container_port = 8501
            protocol       = "TCP"
          }

          env {
            name  = "OTEL_EXPORTER_OTLP_ENDPOINT"
            value = "http://${kubernetes_service.otel_collector.metadata[0].name}.${kubernetes_namespace.opentelemtry.metadata[0].name}.svc.cluster.local:4317"
          }
          
          env {
            name = "OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED"
            value = "true"
          }

          env {
            name  = "ORDER_SERVICE_URL"
            value = local.order_service_url
          }
          env {
            name  = "USER_SERVICE_URL"
            value = local.user_service_url
          }
          env {
            name  = "PRODUCT_SERVICE_URL"
            value = local.product_service_url
          }
          env {
            name  = "CART_SERVICE_URL"
            value = local.cart_service_url
          }
        }
      }
    }
  }
  depends_on = [docker_registry_image.online_store_ui]
}

resource "kubernetes_service" "online_store_ui" {
  metadata {
    name      = "ui"
    namespace = kubernetes_namespace.online_store.metadata[0].name
  }

  spec {
    selector = {
      app = "online-store-ui"
    }

    port {
      name        = "port-80"
      port        = 80
      target_port = 8501
      protocol    = "TCP"
    }

    type = "LoadBalancer"
  }
}