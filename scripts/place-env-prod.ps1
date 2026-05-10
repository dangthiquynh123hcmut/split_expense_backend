#!/usr/bin/env pwsh
# scripts/place-env-prod.ps1
# Đặt .env.prod lên tất cả EC2 instances trong ASG via SSM Send Command

param(
    [string]$EnvFile = "$PSScriptRoot\..\env\.env.prod",
    [string]$Region = "ap-southeast-1",
    [string]$AsgName = "split-expense-asg",
    [string]$AwsCli = ".\venv\Scripts\python.exe -m awscli"
)

Set-Location "$PSScriptRoot\.."

$pythonExe = ".\venv\Scripts\python.exe"

function aws-cli {
    & $pythonExe -m awscli @args
}

Write-Host "=== [1/3] Lay danh sach instances trong ASG ===" -ForegroundColor Cyan

$instancesJson = aws-cli ec2 describe-instances `
    --region $Region `
    --filters "Name=tag:aws:autoscaling:groupName,Values=$AsgName" "Name=instance-state-name,Values=running" `
    --query "Reservations[].Instances[].InstanceId" `
    --output json

$instanceIds = $instancesJson | ConvertFrom-Json
Write-Host "Tim thay $($instanceIds.Count) instances: $($instanceIds -join ', ')" -ForegroundColor Green

if ($instanceIds.Count -eq 0) {
    Write-Error "Khong tim thay instance nao dang running trong ASG $AsgName"
    exit 1
}

Write-Host ""
Write-Host "=== [2/3] Ma hoa .env.prod bang base64 ===" -ForegroundColor Cyan

$envContent = Get-Content $EnvFile -Raw -Encoding UTF8
$envBytes = [System.Text.Encoding]::UTF8.GetBytes($envContent)
$envBase64 = [System.Convert]::ToBase64String($envBytes)
Write-Host "File da ma hoa ($($envBytes.Length) bytes)" -ForegroundColor Green

Write-Host ""
Write-Host "=== [3/3] Gui file len tung instance ===" -ForegroundColor Cyan

$shellScript = @"
#!/bin/bash
set -e
mkdir -p /opt/split-expense-backend/env
echo '$envBase64' | base64 -d > /opt/split-expense-backend/env/.env.prod
chmod 600 /opt/split-expense-backend/env/.env.prod
chown root:root /opt/split-expense-backend/env/.env.prod
echo ".env.prod da duoc tao thanh cong"
ls -la /opt/split-expense-backend/env/
"@

foreach ($instanceId in $instanceIds) {
    Write-Host "  -> Gui len $instanceId ..." -ForegroundColor Yellow

    $commandId = aws-cli ssm send-command `
        --region $Region `
        --instance-ids $instanceId `
        --document-name "AWS-RunShellScript" `
        --parameters "commands=['#!/bin/bash','mkdir -p /opt/split-expense-backend/env','echo $envBase64 | base64 -d > /opt/split-expense-backend/env/.env.prod','chmod 600 /opt/split-expense-backend/env/.env.prod','echo done']" `
        --query "Command.CommandId" `
        --output text

    Write-Host "     Command ID: $commandId" -ForegroundColor Gray

    # Chờ hoàn tất
    Start-Sleep -Seconds 5
    $status = aws-cli ssm get-command-invocation `
        --region $Region `
        --command-id $commandId `
        --instance-id $instanceId `
        --query "Status" `
        --output text 2>$null

    $retries = 0
    while ($status -eq "InProgress" -or $status -eq "Pending" -and $retries -lt 10) {
        Start-Sleep -Seconds 3
        $status = aws-cli ssm get-command-invocation `
            --region $Region `
            --command-id $commandId `
            --instance-id $instanceId `
            --query "Status" `
            --output text 2>$null
        $retries++
    }

    if ($status -eq "Success") {
        Write-Host "     [OK] $instanceId - .env.prod da duoc dat thanh cong" -ForegroundColor Green
    } else {
        Write-Host "     [WARN] $instanceId - Status: $status (kiem tra SSM console)" -ForegroundColor Red
        # In stdout/stderr
        aws-cli ssm get-command-invocation `
            --region $Region `
            --command-id $commandId `
            --instance-id $instanceId `
            --query "[StandardOutputContent,StandardErrorContent]" `
            --output text
    }
}

Write-Host ""
Write-Host "=== Hoan tat! ===" -ForegroundColor Green
Write-Host "Buoc tiep theo: git push de trigger CI/CD pipeline"
