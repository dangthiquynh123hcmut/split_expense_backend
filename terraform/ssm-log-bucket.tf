# terraform/ssm-log-bucket.tf
# S3 bucket để lưu output logs của SSM Run Command

resource "aws_s3_bucket" "ssm_logs" {
  bucket = "${var.project_name}-ssm-logs-${var.aws_region}"
  tags   = { Name = "${var.project_name}-ssm-logs" }
}

resource "aws_s3_bucket_lifecycle_configuration" "ssm_logs" {
  bucket = aws_s3_bucket.ssm_logs.id

  rule {
    id     = "expire-old-logs"
    status = "Enabled"

    expiration {
      days = 30
    }

    filter {
      prefix = "ssm-logs/"
    }
  }
}

output "ssm_log_bucket" {
  description = "S3 bucket name cho SSM logs (dùng làm GitHub Secret: SSM_LOG_BUCKET)"
  value       = aws_s3_bucket.ssm_logs.bucket
}
