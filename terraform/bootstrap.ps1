#!/usr/bin/env pwsh
# Bootstrap script: tao S3 bucket va OIDC resources truoc
# Chay: cd terraform ; .\bootstrap.ps1

Set-Location $PSScriptRoot

Write-Host "=== [1/3] Xoa .terraform cu ===" -ForegroundColor Yellow
Remove-Item -Recurse -Force ".terraform" -ErrorAction SilentlyContinue
Remove-Item -Force "terraform.tfstate" -ErrorAction SilentlyContinue
Remove-Item -Force "terraform.tfstate.backup" -ErrorAction SilentlyContinue
Write-Host "Done." -ForegroundColor Green

Write-Host "=== [2/3] terraform init (local backend) ===" -ForegroundColor Yellow
terraform init
if ($LASTEXITCODE -ne 0) { Write-Error "terraform init failed"; exit 1 }
Write-Host "Done." -ForegroundColor Green

Write-Host "=== [3/3] terraform apply (bootstrap targets) ===" -ForegroundColor Yellow
terraform apply `
    "-target=aws_s3_bucket.tf_state" `
    "-target=aws_s3_bucket_versioning.tf_state" `
    "-target=aws_s3_bucket_server_side_encryption_configuration.tf_state" `
    "-target=aws_s3_bucket.ssm_logs" `
    "-target=aws_iam_openid_connect_provider.github_oidc" `
    "-target=aws_iam_role.github_actions_role" `
    "-target=aws_iam_role_policy.github_actions_policy" `
    -auto-approve
if ($LASTEXITCODE -ne 0) { Write-Error "terraform apply failed"; exit 1 }

Write-Host "=== Bootstrap DONE! ===" -ForegroundColor Green
Write-Host "Buoc tiep theo:" -ForegroundColor Cyan
Write-Host "  1. Uncomment backend block trong main.tf" -ForegroundColor Cyan
Write-Host "  2. terraform init -migrate-state" -ForegroundColor Cyan
Write-Host "  3. terraform apply (full)" -ForegroundColor Cyan
