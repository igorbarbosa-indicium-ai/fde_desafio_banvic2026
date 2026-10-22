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

resource "kubernetes_deployment_v1" "airflow" {
  metadata {
    name      = "banvic-airflow"
    namespace = kubernetes_namespace_v1.environment.metadata[0].name
    labels = {
      app = "banvic-airflow"
    }
  }

  spec {
    replicas = var.pod_replicas

    selector {
      match_labels = {
        app = "banvic-airflow"
      }
    }

    template {
      metadata {
        labels = {
          app = "banvic-airflow"
        }
      }

      spec {
        container {
          name              = "airflow"
          image             = var.airflow_image
          image_pull_policy = "IfNotPresent"
          command           = ["airflow", "standalone"]

          port {
            container_port = 8080
          }

          env_from {
            secret_ref {
              name = "banvic-airflow-runtime"
            }
          }

          volume_mount {
            name       = "incoming"
            mount_path = "/data/incoming"
          }
        }

        volume {
          name = "incoming"

          host_path {
            path = "/mnt/banvic-incoming"
            type = "Directory"
          }
        }
      }
    }
  }
}

resource "kubernetes_service_v1" "airflow" {
  metadata {
    name      = "banvic-airflow"
    namespace = kubernetes_namespace_v1.environment.metadata[0].name
    labels = {
      app = "banvic-airflow"
    }
  }

  spec {
    type = "LoadBalancer"

    selector = {
      app = "banvic-airflow"
    }

    port {
      name        = "http"
      port        = 8080
      target_port = 8080
    }
  }
}
