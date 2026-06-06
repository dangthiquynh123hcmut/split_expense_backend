# terraform/oidc.tf
# Tạo GitHub OIDC Provider và IAM Role cho GitHub Actions
# Chạy file này TRƯỚC khi chạy main.tf
# Đây là "protected resources" – KHÔNG bị destroy khi chạy workflow destroy

# Lấy TLS cert của GitHub OIDC endpoint
data "tls_certificate" "github" {
  url = "https://token.actions.githubusercontent.com/.well-known/openid-configuration"
}

# ── GitHub OIDC Provider ───────────────────────────────────────
resource "aws_iam_openid_connect_provider" "github_oidc" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = ["sts.amazonaws.com"]

  thumbprint_list = data.tls_certificate.github.certificates[*].sha1_fingerprint

  tags = { Name = "github-oidc-provider" }
}

# ── IAM Role cho GitHub Actions ───────────────────────────────
resource "aws_iam_role" "github_actions_role" {
  name = "github-actions-split-expense-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.github_oidc.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          # Chỉ cho phép repo này dùng role này
          "token.actions.githubusercontent.com:sub" = "repo:dangthiquynh123hcmut/split_expense_backend:*"
        }
      }
    }]
  })

  tags = { Name = "github-actions-role" }
}

# Policy cho phép GitHub Actions deploy
resource "aws_iam_role_policy" "github_actions_policy" {
  name = "github-actions-deploy-policy"
  role = aws_iam_role.github_actions_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # Đọc thông tin ASG để lấy instance IDs
        Effect = "Allow"
        Action = [
          "autoscaling:DescribeAutoScalingGroups",
          "autoscaling:DescribeAutoScalingInstances"
        ]
        Resource = "*"
      },
      {
        # Lấy IP của EC2 instances
        Effect   = "Allow"
        Action   = ["ec2:DescribeInstances"]
        Resource = "*"
      },
      {
        # SSM Run Command để chạy deploy script trên EC2
        Effect = "Allow"
        Action = [
          "ssm:SendCommand",
          "ssm:GetCommandInvocation",
          "ssm:ListCommandInvocations",
          "ssm:WaitUntilCommandExecuted"
        ]
        Resource = "*"
      },
      {
        # Describe ALB để lấy DNS cho health check
        Effect   = "Allow"
        Action   = ["elasticloadbalancing:DescribeLoadBalancers"]
        Resource = "*"
      },
      {
        # Đọc/ghi S3 bucket cho SSM output logs
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = "*"
      },
      {
        # Terraform state
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = "*"
      }
    ]
  })
}

# ── S3 bucket cho Terraform state (protected) ──────────────────
resource "aws_s3_bucket" "tf_state" {
  bucket = "split-expense-tf-state-${var.aws_region}"
  tags   = { Name = "terraform-state" }
}

resource "aws_s3_bucket_versioning" "tf_state" {
  bucket = aws_s3_bucket.tf_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tf_state" {
  bucket = aws_s3_bucket.tf_state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# ── Outputs ────────────────────────────────────────────────────
output "github_actions_role_arn" {
  description = "ARN của IAM Role (dùng làm GitHub Secret: AWS_ROLE_ARN)"
  value       = aws_iam_role.github_actions_role.arn
}

output "tf_state_bucket" {
  description = "S3 bucket name cho Terraform state (dùng làm GitHub Secret: TF_STATE_BUCKET)"
  value       = aws_s3_bucket.tf_state.bucket
}
