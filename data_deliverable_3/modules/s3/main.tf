resource "aws_s3_bucket" "many_buckets" {
  #bucket name should be unique
  count         = length(var.bucket_prefixes)
  bucket_prefix = var.bucket_prefixes[count.index]
  
  versioning {
    enabled = var.versioning
  }

  tags = {
    Name = "s3-data-bootcamp"
  }
}

resource "aws_s3_bucket_public_access_block" "many_buckets" {
  count         = length(var.bucket_prefixes)
  bucket        = aws_s3_bucket.many_buckets[count.index].id

  block_public_acls      = true
  block_public_policy    = true
  ignore_public_acls     = true
  restrict_public_buckets = true
}