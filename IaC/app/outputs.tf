output "jaeger_loadbalancer_ip" {
  value = kubernetes_service.jaeger_lb.status[0].load_balancer[0].ingress[0].ip
}

output "grafana_loadbalancer_ip" {
  value = kubernetes_service.grafana.status[0].load_balancer[0].ingress[0].ip
}