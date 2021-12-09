variable "bucket_prefixes" {
  type = list(string)
  default = ["raw-layer", "staging-layer", "analytics-layer", "spark-files"]
}

variable "acl" {
  type = string
  default = "private"
}

variable "versioning" {
  type = bool
}

variable "subnet_s3" {
  type = list(string)
}

variable "vpc_id_s3" {
  description = "VPC id"
}
