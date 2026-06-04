# terraform/rds.tf
# RDS PostgreSQL instance – đặt trong private subnets, chỉ EC2 được kết nối

# ── DB Subnet Group ────────────────────────────────────────────
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = { Name = "${var.project_name}-db-subnet-group" }
}

# ── Security Group cho RDS ─────────────────────────────────────
resource "aws_security_group" "rds" {
  name        = "${var.project_name}-rds-sg"
  description = "RDS: allow PostgreSQL from EC2 security group only"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }

  tags = { Name = "${var.project_name}-rds-sg" }
}

# ── RDS Instance ───────────────────────────────────────────────
resource "aws_db_instance" "main" {
  identifier = "${var.project_name}-db"

  engine         = "postgres"
  engine_version = "16"
  instance_class = var.rds_instance_class

  allocated_storage     = var.rds_allocated_storage
  max_allocated_storage = var.rds_max_storage
  storage_encrypted     = true
  storage_type          = "gp3"

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  port = 5432

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  publicly_accessible    = false
  multi_az               = false
  backup_retention_period = var.rds_backup_retention_days
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"

  deletion_protection = false
  skip_final_snapshot = false
  final_snapshot_identifier = "${var.project_name}-db-final-${formatdate("YYYYMMDDhhmmss", timestamp())}"

  enabled_cloudwatch_logs_exports = ["postgresql"]
  performance_insights_enabled    = false   # Free Tier không hỗ trợ

  tags = { Name = "${var.project_name}-rds" }
}

# ── SSM Parameter: DATABASE_URL (tự động tạo từ RDS endpoint) ─
# EC2 sẽ fetch parameter này khi boot để có connection string
resource "aws_ssm_parameter" "database_url" {
  name  = "/${var.project_name}/prod/database-url"
  type  = "SecureString"
  value = "postgres://${var.db_username}:${var.db_password}@${aws_db_instance.main.endpoint}/${var.db_name}?sslmode=require"

  tags = { Name = "${var.project_name}-db-url" }
}

# ── Outputs ────────────────────────────────────────────────────
output "rds_endpoint" {
  description = "RDS endpoint (host:port)"
  value       = aws_db_instance.main.endpoint
}

output "rds_address" {
  description = "RDS hostname (không có port)"
  value       = aws_db_instance.main.address
}

output "rds_port" {
  description = "RDS port"
  value       = aws_db_instance.main.port
}

output "rds_db_name" {
  description = "Database name"
  value       = aws_db_instance.main.db_name
}

output "rds_ssm_parameter" {
  description = "SSM Parameter path chứa DATABASE_URL"
  value       = aws_ssm_parameter.database_url.name
}
