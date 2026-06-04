# ============================================================
# Fix EC2 - gửi lệnh sửa firebase.json và restart Docker
# ============================================================
param(
    [string]$Region = "ap-southeast-1",
    [string]$InstanceId = ""
)

$ErrorActionPreference = "Stop"

# Nếu không có InstanceId, tự tìm từ ASG
if (-not $InstanceId) {
    Write-Host "Finding running EC2 instance in ASG split-expense-asg..."
    $asgInstances = & aws autoscaling describe-auto-scaling-groups `
        --region $Region `
        --auto-scaling-group-names "split-expense-asg" `
        --query "AutoScalingGroups[0].Instances[?LifecycleState=='InService'].InstanceId" `
        --output text 2>&1

    if ($LASTEXITCODE -ne 0 -or -not $asgInstances) {
        Write-Host "ERROR: Cannot find instances from ASG. Provide -InstanceId manually." -ForegroundColor Red
        exit 1
    }

    $instanceIds = $asgInstances -split '\s+'
    $InstanceId = $instanceIds[0]
    Write-Host "  Found: $InstanceId"
}

Write-Host "Target instance: $InstanceId" -ForegroundColor Green

# Commands to run on EC2
$commands = @(
    'cd /opt/split-expense-backend',
    'docker compose -f docker-compose.prod.yml down',
    'rm -rf firebase.json',
    'aws ssm get-parameter --region ap-southeast-1 --name /split-expense/prod/firebase --with-decryption --query "Parameter.Value" --output text > firebase.json',
    'chmod 600 firebase.json',
    'echo "Size: $(wc -c < firebase.json) bytes"',
    'python3 -c "import json; d=json.load(open(\"firebase.json\")); print(\"type:\", d[\"type\"])"',
    'docker compose -f docker-compose.prod.yml up -d 2>&1',
    'sleep 15',
    'echo "=== CONTAINER STATUS ==="',
    'docker ps --filter "name=split_expense" --format "table {{.Names}}\t{{.Status}}"',
    'echo ""',
    'echo "=== DJANGO LOGS (last 10) ==="',
    'docker logs split_expense_backend_prod 2>&1 | tail -10'
)

Write-Host "`nSending SSM command..."
$cmdJson = $commands | ConvertTo-Json -Compress

$result = & aws ssm send-command `
    --region $Region `
    --instance-ids $InstanceId `
    --document-name "AWS-RunShellScript" `
    --parameters "{\"commands\":$cmdJson}" `
    --output json 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR sending command:" -ForegroundColor Red
    Write-Host $result
    exit 1
}

$cmdData = $result | ConvertFrom-Json
$cmdId = $cmdData.Command.CommandId
Write-Host "  Command ID: $cmdId" -ForegroundColor Green

# Wait for completion
Write-Host "`nWaiting for completion..."
for ($i = 1; $i -le 30; $i++) {
    Start-Sleep -Seconds 5
    $inv = & aws ssm get-command-invocation `
        --region $Region `
        --command-id $cmdId `
        --instance-id $InstanceId `
        --output json 2>&1

    if ($LASTEXITCODE -eq 0) {
        $invData = $inv | ConvertFrom-Json
        $status = $invData.Status
        Write-Host "  Attempt $i : $status"
        if ($status -in @("Success", "Failed", "Cancelled", "TimedOut")) {
            break
        }
    }
}

# Show output
Write-Host "`n=== STDOUT ==="
Write-Host $invData.StandardOutputContent

if ($invData.StandardErrorContent) {
    Write-Host "`n=== STDERR ==="
    Write-Host $invData.StandardErrorContent
}

Write-Host "`n=== Status: $($invData.Status) ==="
