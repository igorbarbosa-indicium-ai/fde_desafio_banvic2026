variable "environment" {
  description = "Deployment environment: dev, hom, or prod."
  type        = string

  validation {
    condition     = contains(["dev", "hom", "prod"], var.environment)
    error_message = "environment must be one of: dev, hom, prod."
  }
}

variable "kubeconfig_path" {
  description = "Path to the kubeconfig used by the Kubernetes provider."
  type        = string
  default     = "~/.kube/config"
}

variable "kube_context" {
  description = "Kubernetes context to target."
  type        = string
  default     = "kind-banvic"
}

variable "airflow_image" {
  description = "Airflow image already loaded into the Kind cluster."
  type        = string
  default     = "banvic-elt:dev"
}

variable "pod_replicas" {
  description = "Number of Airflow pods managed behind the LoadBalancer Service."
  type        = number
  default     = 2

  validation {
    condition     = var.pod_replicas >= 2
    error_message = "pod_replicas must be at least 2 for the load-balanced setup."
  }
}