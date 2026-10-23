output "bucket_names" {
  description = "Map nom logique → nom réel du bucket (ex. raw → data-platform-dev-raw-<account_id>)."
  value       = { for k, b in aws_s3_bucket.this : k => b.bucket }
}

output "bucket_arns" {
  description = "Map nom logique → ARN du bucket."
  value       = { for k, b in aws_s3_bucket.this : k => b.arn }
}
