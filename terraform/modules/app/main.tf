variable name {}
variable namespace {}
variable env_map {}
variable replicas {}
variable image {}
variable image_pull_secrets {}
variable node_port {}
variable container_port {}

resource "kubernetes_config_map_v1" "app-config-map-v1" {
  metadata {
    name = var.name
    namespace = var.namespace
  }
  data = var.env_map
}

resource "kubernetes_deployment_v1" "app-deployment-v1" {
  metadata {
    name      = var.name
    namespace = var.namespace
  }
  spec {
    replicas = var.replicas
    selector {
      match_labels = {
        app = var.name
      }
    }
    template {
      metadata {
        labels = {
          app = var.name
        }
      }
      spec {
        container {
          image = var.image
          image_pull_policy = "Always"
          name  = var.name
          port {
            container_port = var.container_port
          }

          env_from {
            config_map_ref {
              name = kubernetes_config_map_v1.app-config-map-v1.metadata[0].name
            }
          }

        }
        image_pull_secrets {
          name = var.image_pull_secrets
        }
      }
    }
  }
}

resource "kubernetes_service_v1" "app-service" {

  metadata {
    name      = var.name
    namespace = var.namespace
  }

  spec {
    selector = {
      app = kubernetes_deployment_v1.app-deployment-v1.spec.0.template.0.metadata.0.labels.app
    }
    type = "NodePort"
    port {
      node_port   = var.node_port
      port        = 80
      target_port = var.container_port
    }
  }
}
