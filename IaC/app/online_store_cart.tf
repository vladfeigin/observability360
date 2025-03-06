locals {
  online_store_cart_image_name     = "${local.online_store_docker_images_name_prefix}-cart:latest"
  online_store_cart_directory_name = "cart"
  online_store_cart_directory_path = "${local.online_store_directory_path}/${local.online_store_cart_directory_name}"
}


resource "docker_image" "online_store_cart" {
  name         = "${data.azurerm_container_registry.demo.login_server}/${local.online_store_cart_image_name}"
  keep_locally = false

  build {
    context    = "${path.cwd}/${local.online_store_directory_path}"
    dockerfile = "${local.online_store_cart_directory_name}/Dockerfile"
    platform   = "linux/amd64"
  }

  triggers = {
    dir_sha1      = sha1(join("", [for f in fileset(path.cwd, "${local.online_store_cart_directory_path}/*") : filesha1(f)]))
    dir_sha1_otel = sha1(join("", [for f in fileset(path.cwd, "${local.online_store_otel_directory_path}/*") : filesha1(f)]))
  }
}

resource "docker_registry_image" "online_store_cart" {
  name          = docker_image.online_store_cart.name
  keep_remotely = true

  triggers = {
    dir_sha1      = sha1(join("", [for f in fileset(path.cwd, "${local.online_store_cart_directory_path}/*") : filesha1(f)]))
    dir_sha1_otel = sha1(join("", [for f in fileset(path.cwd, "${local.online_store_otel_directory_path}/*") : filesha1(f)]))
  }
}


resource "kubernetes_deployment" "online_store_cart" {
  metadata {
    name      = "online-store-cart"
    namespace = kubernetes_namespace.online_store.metadata[0].name
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = "online-store-cart"
      }
    }

    template {
      metadata {
        labels = {
          app = "online-store-cart"
        }
      }

      spec {
        container {
          name  = "online-store-cart"
          image = docker_registry_image.online_store_cart.name
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
            container_port = 5002
            protocol       = "TCP"
          }

          env {
            name  = "OTEL_EXPORTER_OTLP_ENDPOINT"
            value = "http://${kubernetes_service.otel_collector.metadata[0].name}.${kubernetes_namespace.opentelemtry.metadata[0].name}.svc.cluster.local:4317"
          }

          volume_mount {
            name       = "online-store-db"
            mount_path = "/app/online_store/db"
          }

        }
        volume {
          name = "online-store-db"
          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim.online_store_db.metadata[0].name
          }
        }
      }
    }
  }

  depends_on = [docker_registry_image.online_store_cart]
}

resource "kubernetes_service" "online_store_cart" {
  metadata {
    name      = "cart"
    namespace = kubernetes_namespace.online_store.metadata[0].name
  }

  spec {
    selector = {
      app = "online-store-cart"
    }

    port {
      name        = "port-80"
      port        = 80
      target_port = 5002
      protocol    = "TCP"
    }

    type = "ClusterIP"
  }
}