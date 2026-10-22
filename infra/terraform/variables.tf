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
  description = "Kubernetes context to target, for example rancher-desktop."
  type        = string
  default     = "rancher-desktop"
}