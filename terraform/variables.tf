# terraform/variables.tf

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "ap-southeast-1"
}

variable "project_name" {
  description = "Project name prefix for all resources"
  type        = string
  default     = "split-expense"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.small"
}

variable "docker_image" {
  description = "Docker Hub image (e.g. username/split-expense-backend)"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository in format owner/repo"
  type        = string
  default     = "dangthiquynh123hcmut/split_expense_backend"
}

variable "asg_min_size" {
  description = "Minimum number of EC2 instances in ASG"
  type        = number
  default     = 1
}

variable "asg_max_size" {
  description = "Maximum number of EC2 instances in ASG"
  type        = number
  default     = 1
}

variable "asg_desired_capacity" {
  description = "Desired number of EC2 instances in ASG"
  type        = number
  default     = 1
}

# ── RDS ────────────────────────────────────────────
variable "rds_instance_class" {
  description = "RDS instance type"
  type        = string
  default     = "db.t4g.micro"
}

variable "rds_allocated_storage" {
  description = "Allocated storage (GB)"
  type        = number
  default     = 20
}

variable "rds_max_storage" {
  description = "Max storage với autoscaling (GB)"
  type        = number
  default     = 100
}

variable "rds_backup_retention_days" {
  description = "Số ngày giữ backup (Free Tier: tối đa 1)"
  type        = number
  default     = 1
}

variable "db_name" {
  description = "Tên database"
  type        = string
  default     = "split_expense_db"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "split_expense_admin"
}

variable "certificate_arn" {
  description = "ARN của ACM certificate cho HTTPS listener (cần tạo trên tài khoản mới)"
  type        = string
  # Bắt buộc set trong terraform.tfvars
}

variable "db_password" {
  description = "Database master password – TRUYỀN QUA ENV: TF_VAR_db_password"
  type        = string
  sensitive   = true
  # Không có default — bắt buộc set qua environment variable
}
