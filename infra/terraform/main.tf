resource "kubernetes_namespace_v1" "environment" {
  metadata {
    name = "banvic-${var.environment}"
    labels = {
      app         = "banvic-elt"
      environment = var.environment
      managed-by  = "terraform"
    }
  }
}