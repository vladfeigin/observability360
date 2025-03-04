locals {
  online_store_namespace_name = "online-store"

  online_store_directory_path = "../../online_store"
  online_store_docker_images_name_prefix = "${var.base_name}-online-store"

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