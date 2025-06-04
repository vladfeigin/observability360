output "jaeger_loadbalancer_ip" {
  value = kubernetes_service.jaeger_lb.status[0].load_balancer[0].ingress[0].ip
}

output "grafana_loadbalancer_ip" {
  value = kubernetes_service.grafana.status[0].load_balancer[0].ingress[0].ip
}

output "online_store_ui_loadbalancer_ip" {
  value = kubernetes_service.online_store_ui.status[0].load_balancer[0].ingress[0].ip
}

output "fabric_kql_database_permissions_commands" {
  value = !var.is_fabric ? null : <<EOT
run the following kql queries to add permisions to the workloads:
.add database ['observabilitydb'] ingestors ('aadapp=${azuread_service_principal.otel.object_id}')
.add database ['observabilitydb'] viewers ('aadapp=${azuread_service_principal.jaeger.object_id}')
.add database ['observabilitydb'] viewers ('aadapp=${azuread_service_principal.grafana.object_id}')
  EOT 
}