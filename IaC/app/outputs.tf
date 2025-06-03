output "jaeger_loadbalancer_ip" {
  value = kubernetes_service.jaeger_lb.status[0].load_balancer[0].ingress[0].ip
}

output "grafana_loadbalancer_ip" {
  value = kubernetes_service.grafana.status[0].load_balancer[0].ingress[0].ip
}

output "online_store_ui_loadbalancer_ip" {
  value = kubernetes_service.online_store_ui.status[0].load_balancer[0].ingress[0].ip
}

output "test" {
  value = !var.is_fabric ? null : <<EOT
    run the following kql queries to add permisions to the workloads:
    .add database ['${var.base_name}-kql-database'] ingestors ('aadapp=${azuread_service_principal.otel.object_id}')
    .add database ['${var.base_name}-kql-database'] viewers ('aadapp=${azuread_service_principal.jaeger.object_id}')
    .add database ['${var.base_name}-kql-database'] viewers ('aadapp=${azuread_service_principal.grafana_to_adx.object_id}')
  EOT 
}