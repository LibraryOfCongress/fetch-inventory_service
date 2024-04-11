terraform {

  backend "http" {
  }

  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.0"
    }
  }
}

variable vault_deployer_username { default = "deployer" }
variable vault_deployer_password {}
variable vault_addr {}
variable app_name {}

provider "vault" {
  address = var.vault_addr
  skip_child_token = true
  auth_login_userpass {
    username = var.vault_deployer_username
    password = var.vault_deployer_password
  }
}

data "vault_generic_secret" "env" {
  path = "fetch/${var.app_name}/env"
}

locals {

  env_string = data.vault_generic_secret.env.data["key"]
  lines = split("\n", local.env_string)
  filtered_lines = [for line in local.lines : line if line != "" && can(split("=", line))]
  env_map = {
    for line in local.filtered_lines : element(split("=", line), 0) => element(split("=", line), 1)
  }

}

provider "kubernetes" {
  # config_path = "~/.kube/config"
  config_path = "${path.module}/kubeconfig"
}

variable "image" {}

locals {
  namespace = "fetch"
}

module "app" {
  source = "./modules/app"
  name = var.app_name
  namespace = local.namespace
  image = var.image
  env_map = local.env_map
  replicas = 1
  image_pull_secrets = "gitlab-api-2023"
  node_port = 30100
  container_port = 8001
}
