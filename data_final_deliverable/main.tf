
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

module "rds" {
  source = "./modules/rds"

  vpc_id_rds          = module.networking.vpc_id
  subnets_rds         = module.networking.private_subnets_ids

  allocated_storage   = var.allocated_storage
  db_engine           = var.db_engine
  db_port             = var.db_port
  engine_version      = var.engine_version
  instance_type       = var.instance_type
  database_name       = var.database_name
  db_username         = var.db_username
  db_password         = var.db_password
  publicly_accessible = var.publicly_accessible
}

module "s3" {
    source = "./modules/s3"
    acl           = "private"
    versioning    = true

    vpc_id_s3 = module.networking.vpc_id
    subnet_s3 = module.networking.private_subnets_ids
}


resource "aws_subnet" "redshift_subnet_1" {
  vpc_id     = "${module.networking.vpc_id}"
  cidr_block        = "${var.redshift_subnet_cidr_1}"
  availability_zone = "us-east-2a"
  map_public_ip_on_launch = "true"
tags = {
    Name = "redshift-subnet-1"
  }
depends_on = [
    module.networking
  ]
}
resource "aws_subnet" "redshift_subnet_2" {
  vpc_id     = "${module.networking.vpc_id}"
  cidr_block        = "${var.redshift_subnet_cidr_2}"
  availability_zone = "us-east-2b"
  map_public_ip_on_launch = "true"
tags = {
    Name = "redshift-subnet-2"
  }
depends_on = [
    module.networking
  ]
}

resource "aws_redshift_subnet_group" "redshift_subnet_group" {
  name       = "redshift-subnet-group"
  subnet_ids = ["${aws_subnet.redshift_subnet_1.id}", "${aws_subnet.redshift_subnet_2.id}"]
tags = {
    environment = "dev"
    Name = "redshift-subnet-group"
  }
}

resource "aws_redshift_cluster" "default" {
  cluster_identifier = "${var.rs_cluster_identifier}"
  database_name      = "${var.rs_database_name}"
  master_username    = "${var.rs_master_username}"
  master_password    = "${var.rs_master_pass}"
  node_type          = "${var.rs_nodetype}"
  cluster_type       = "${var.rs_cluster_type}"
  cluster_subnet_group_name = "${aws_redshift_subnet_group.redshift_subnet_group.id}"
  skip_final_snapshot = true

  depends_on = [
    module.networking,
    module.networking.aws_security_group,
    aws_redshift_subnet_group.redshift_subnet_group,
  ]
}
