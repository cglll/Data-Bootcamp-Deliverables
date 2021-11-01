provider "aws" {
  access_key = "AKIA4OG2YBTBV6OLEVMG"
  secret_key = "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"
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
