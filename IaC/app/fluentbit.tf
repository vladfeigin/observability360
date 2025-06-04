locals {
  fluentbit_directory_path = "../../fluentbit"
}


resource "kubernetes_namespace" "fluentbit" {
  metadata {
    name = "fluentbit"
  }
}

resource "kubernetes_service_account" "fluentbit" {
  metadata {
    name      = "fluent-bit"
    namespace = kubernetes_namespace.fluentbit.metadata[0].name
  }
}

resource "kubernetes_cluster_role" "fluentbit" {
  metadata {
    name = "fluent-bit-read"
  }

  rule {
    api_groups = [""]
    resources  = ["namespaces", "pods", "events"]
    verbs      = ["get", "list", "watch"]
  }
}


resource "kubernetes_cluster_role_binding" "fluentbit" {
  metadata {
    name = "fluent-bit-read"
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "ClusterRole"
    name      = "fluent-bit-read"
  }

  subject {
    kind      = "ServiceAccount"
    name      = "fluent-bit"
    namespace = kubernetes_namespace.fluentbit.metadata[0].name
  }
}

resource "kubernetes_config_map" "fluentbit" {
  metadata {
    name      = "fluent-bit-config"
    namespace = kubernetes_namespace.fluentbit.metadata[0].name
  }

  data = {
    "fluent-bit.conf" = templatefile("${path.cwd}/${local.fluentbit_directory_path}/fluent-bit.conf.tftpl", {
      otel_collector_service_name   = kubernetes_service.otel_collector.metadata[0].name,
      otel_collector_namespace_name = kubernetes_namespace.opentelemtry.metadata[0].name,
      aks_name                      = data.azurerm_kubernetes_cluster.demo.name,
      region_name                   = var.region,
      environment_name              = var.base_name
    })
    "parsers.conf" = file("${path.cwd}/${local.fluentbit_directory_path}/parsers.conf")
  }
}

resource "kubernetes_daemonset" "fluentbit" {
  metadata {
    name      = "fluent-bit"
    namespace = kubernetes_namespace.fluentbit.metadata[0].name
    labels = {
      app = "fluent-bit"
      "kubernetes.io/cluster-service" : "true"
    }
  }

  spec {
    selector {
      match_labels = {
        app = "fluent-bit"
      }
    }

    template {
      metadata {
        labels = {
          app = "fluent-bit"
          "kubernetes.io/cluster-service" : "true"
        }
      }

      spec {
        service_account_name = kubernetes_service_account.fluentbit.metadata[0].name

        container {
          name  = "fluent-bit"
          image = "fluent/fluent-bit"

          volume_mount {
            name       = "fluent-bit-config"
            mount_path = "/fluent-bit/etc/"
          }
          volume_mount {
            name       = "varlog"
            mount_path = "/var/log/"
          }
          volume_mount {
            name       = "varlibdockercontainers"
            mount_path = "/var/lib/docker/containers/"
            read_only  = true
          }
        }

        volume {
          name = "fluent-bit-config"

          config_map {
            name = kubernetes_config_map.fluentbit.metadata[0].name
          }
        }
        volume {
          name = "varlog"

          host_path {
            path = "/var/log"
          }
        }
        volume {
          name = "varlibdockercontainers"

          host_path {
            path = "/var/lib/docker/containers"
          }
        }
      }
    }
  }
}