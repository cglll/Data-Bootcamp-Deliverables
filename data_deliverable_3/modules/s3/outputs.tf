output "s3_bucket_id" {
    value = join("", aws_s3_bucket.many_buckets[*].id)
}
output "s3_bucket_arn" {
    value = join("", aws_s3_bucket.many_buckets[*].arn)
}
output "s3_bucket_domain_name" {
    value = join("", aws_s3_bucket.many_buckets[*].bucket_domain_name)
}
output "s3_hosted_zone_id" {
    value = join("", aws_s3_bucket.many_buckets[*].hosted_zone_id)
}
output "s3_bucket_region" {
    value = join("", aws_s3_bucket.many_buckets[*].region)
}