provider "aws" {
  access_key = "access_key"
  secret_key = "secret_key"
  region     = var.region
}
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~>3.0"
    }
  }
}
