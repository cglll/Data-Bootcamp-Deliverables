
module "networking" {
  source = "./modules/networking"

  vpc_cidr             = var.vpc_cidr
  public_subnets_cidr  = var.public_subnets_cidr
  private_subnets_cidr = var.private_subnets_cidr
  availability_zone    = var.availability_zone
}


module "eks" {
  source = "./modules/eks"

  vpc_id_eks = module.networking.vpc_id
  subnet = module.networking.private_subnets_ids

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  instance_type_group1        = var.instance_type_group1
  instance_type_group2        = var.instance_type_group2
  asg_desired_capacity_group1 = var.asg_desired_capacity_group1
  asg_desired_capacity_group2 = var.asg_desired_capacity_group2
}

data "aws_security_group" "default" {
  name   = "default"
  vpc_id = module.vpc.vpc_id
}


# vpc
module "vpc" {
  source             = "terraform-aws-modules/vpc/aws"
  # use 2.7 or newer to prevent "Error: multiple VPC Endpoint Services matched"
  version            = "2.70.0"
  name               = var.name
  azs                = var.azs
  cidr               = "10.0.0.0/16"
  private_subnets    = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  enable_nat_gateway = true
  single_nat_gateway = true

  # enable dns support
  enable_dns_hostnames = true
  enable_dns_support   = true

  # vpc endpoint for s3
  enable_s3_endpoint = true

  # vpc endpoint for ecr
  enable_ecr_api_endpoint              = true
  ecr_api_endpoint_private_dns_enabled = true
  ecr_api_endpoint_security_group_ids  = [data.aws_security_group.default.id]

  enable_ecr_dkr_endpoint              = true
  ecr_dkr_endpoint_private_dns_enabled = true
  ecr_dkr_endpoint_security_group_ids  = [data.aws_security_group.default.id]
}


# ecr
module "ecr" {
  source = "./modules/ecr"
  name   = "apps"
  tags   = var.tags
}