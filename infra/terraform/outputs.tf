output "namespace" {
  description = "Kubernetes namespace for this environment."
  value       = kubernetes_namespace_v1.environment.metadata[0].name
}