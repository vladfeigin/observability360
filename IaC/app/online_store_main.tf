locals {
  online_store_namespace_name = "online-store"

  online_store_directory_path            = "../../online_store"
  online_store_docker_images_name_prefix = "${var.base_name}-online-store"
  online_store_otel_directory_path       = "../../online_store/otel"

  order_service_url   = "http://order.${local.online_store_namespace_name}.svc.cluster.local"
  user_service_url    = "http://user.${local.online_store_namespace_name}.svc.cluster.local"
  product_service_url = "http://product.${local.online_store_namespace_name}.svc.cluster.local"
  cart_service_url    = "http://cart.${local.online_store_namespace_name}.svc.cluster.local"
}

resource "kubernetes_namespace" "online_store" {
  metadata {
    name = local.online_store_namespace_name
  }
}


resource "kubernetes_storage_class" "azurefile" {
  metadata {
    name = "azurefile-custom"
  }
  storage_provisioner = "kubernetes.io/azure-file"
  mount_options = [
    "dir_mode=0777",
    "file_mode=0777",
    "uid=1000",
    "gid=1000",
    "mfsymlinks",
    "nobrl",
    "cache=none"
  ]
  parameters = {
    skuName = "Standard_LRS"
  }
}

resource "kubernetes_persistent_volume_claim" "online_store_db" {
  metadata {
    name      = "online-store-db-pvc"
    namespace = kubernetes_namespace.online_store.metadata[0].name
  }
  spec {
    access_modes = ["ReadWriteMany"]
    resources {
      requests = {
        storage = "5Gi"
      }
    }
    storage_class_name = kubernetes_storage_class.azurefile.metadata[0].name
  }
}