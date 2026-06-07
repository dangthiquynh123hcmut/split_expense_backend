# terraform/s3-file-storage.tf
# S3 bucket để lưu trữ file upload từ application (avatar, expense attachments, message attachments)
# Upload qua presigned URL (PutObject) — Download qua public URL (GetObject công khai)

resource "aws_s3_bucket" "file_storage" {
  bucket = "${var.project_name}-files-${var.aws_region}"
  tags   = { Name = "${var.project_name}-files" }
}

# Chặn ACL public (dùng bucket policy thay thế) — chỉ cho phép GetObject công khai
resource "aws_s3_bucket_public_access_block" "file_storage" {
  bucket                  = aws_s3_bucket.file_storage.id
  block_public_acls       = true
  block_public_policy     = false
  ignore_public_acls      = true
  restrict_public_buckets = false
}

# Bucket policy: cho phép tất cả mọi người GetObject (download/xem file công khai)
resource "aws_s3_bucket_policy" "file_storage_public_read" {
  bucket = aws_s3_bucket.file_storage.id
  depends_on = [aws_s3_bucket_public_access_block.file_storage]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.file_storage.arn}/*"
      }
    ]
  })
}

# CORS để frontend có thể upload trực tiếp lên S3 qua presigned URL
resource "aws_s3_bucket_cors_configuration" "file_storage" {
  bucket = aws_s3_bucket.file_storage.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "DELETE", "HEAD"]
    allowed_origins = [
      "https://split-expense.app",
      "https://www.split-expense.app",
      "https://dividex-admin-dashboard.vercel.app",
      "http://localhost:3000",
    ]
    expose_headers  = ["ETag", "x-amz-request-id"]
    max_age_seconds = 3600
  }
}

# Lifecycle: tự động xoá incomplete multipart uploads sau 7 ngày
resource "aws_s3_bucket_lifecycle_configuration" "file_storage" {
  bucket = aws_s3_bucket.file_storage.id

  rule {
    id     = "abort-incomplete-uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }

    filter {}
  }
}

output "file_storage_bucket" {
  description = "S3 bucket name cho file storage (dùng làm giá trị S3_BUCKET_NAME trong .env.prod)"
  value       = aws_s3_bucket.file_storage.bucket
}
