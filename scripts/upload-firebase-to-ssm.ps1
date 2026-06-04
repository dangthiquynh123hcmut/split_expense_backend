# ============================================================
# Upload Firebase credentials to AWS SSM Parameter Store
# Run from local machine with AWS CLI configured
# ============================================================
param(
    [string]$Region = "ap-southeast-1",
    [string]$ParamName = "/split-expense/prod/firebase",
    [string]$FirebaseFile = "firebase.json"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Resolve-Path "$ScriptDir\.."
$FirebasePath = Join-Path $ProjectDir $FirebaseFile

Write-Host "=== Upload Firebase credentials to SSM ===" -ForegroundColor Green
Write-Host "  Region:       $Region"
Write-Host "  SSM Param:    $ParamName"
Write-Host "  Source file:  $FirebasePath"

if (-not (Test-Path $FirebasePath)) {
    Write-Host "ERROR: File not found: $FirebasePath" -ForegroundColor Red
    exit 1
}

# Validate JSON
try {
    $rawContent = Get-Content -Raw $FirebasePath
    $content = $rawContent | ConvertFrom-Json
    $jsonLen = ($content | ConvertTo-Json -Compress).Length
    Write-Host "  JSON valid ($jsonLen chars)"
}
catch {
    Write-Host "ERROR: Invalid JSON in $FirebasePath" -ForegroundColor Red
    Write-Host $_.Exception.Message
    exit 1
}

# Upload as SecureString (use file:// to avoid shell escaping issues with JSON)
Write-Host ""
Write-Host "Uploading to SSM Parameter Store..."

# Build arguments as array to avoid PowerShell parsing issues
$argList = @(
    "ssm", "put-parameter",
    "--region", $Region,
    "--name", $ParamName,
    "--value", "file://$FirebasePath",
    "--type", "SecureString",
    "--overwrite"
)

Write-Host "  Running: aws $($argList -join ' ')"
$output = & aws $argList 2>&1
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Host "ERROR: Failed to upload to SSM" -ForegroundColor Red
    Write-Host $output
    exit 1
}

Write-Host "  Uploaded successfully" -ForegroundColor Green
Write-Host $output

# Verify
Write-Host ""
Write-Host "Verifying..."
$verifyArgs = @(
    "ssm", "get-parameter",
    "--region", $Region,
    "--name", $ParamName,
    "--with-decryption",
    "--query", "Parameter.Value",
    "--output", "text"
)
$result = & aws $verifyArgs 2>&1

if ($LASTEXITCODE -eq 0 -and $result) {
    try {
        $verifyJson = $result | ConvertFrom-Json
        Write-Host "  Verified - Parameter contains valid JSON with type: $($verifyJson.type)" -ForegroundColor Green
    }
    catch {
        Write-Host "  WARNING: Retrieved value is not valid JSON ($($result.Length) chars)" -ForegroundColor Yellow
        Write-Host "  First 100 chars: $($result.Substring(0, [Math]::Min(100, $result.Length)))"
    }
}
else {
    Write-Host "  WARNING: Verification failed" -ForegroundColor Yellow
    Write-Host $result
}

Write-Host ""
Write-Host "=== Done! ===" -ForegroundColor Green
Write-Host "Next step: Run fix_fb.sh on EC2 to apply the new credentials"
