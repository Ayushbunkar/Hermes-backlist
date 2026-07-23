Write-Host "========================================="
Write-Host "       STARTING HERMES ENGINE            "
Write-Host "========================================="

Write-Host "-> Cleaning up old background processes..."
Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "node" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

Write-Host "-> Verifying Python dependencies..."
pip install -r requirements.txt > $null 2>&1

Write-Host "-> Applying Database Foreign Key fixes..."
python apply_db_fixes.py

Write-Host "-> Clearing Telegram webhook/polling session..."
$env:PYTHONPATH = "workspace-bl-orchestrator/skills/pipeline"
$BOT_TOKEN = (python -c "import config; print(config.TELEGRAM_BOT_TOKEN)" 2>$null)
if ([string]::IsNullOrWhiteSpace($BOT_TOKEN) -eq $false) {
    Invoke-RestMethod -Uri "https://api.telegram.org/bot$($BOT_TOKEN)/deleteWebhook?drop_pending_updates=true" -Method Get > $null
    Write-Host "   Telegram session cleared."
} else {
    Write-Host "   Could not read BOT_TOKEN, skipping webhook clear."
}

Start-Sleep -Seconds 2

Write-Host "-> Starting Telegram Router (Bot Listener)..."
Start-Process -NoNewWindow -FilePath "python" -ArgumentList "workspace-bl-orchestrator/skills/pipeline/telegram_router.py"

Write-Host "-> Resetting any failed leads..."
python reset_leads.py

Write-Host "-> Starting Nexus Daemon (Hunter)..."
Start-Process -NoNewWindow -FilePath "python" -ArgumentList "workspace-bl-orchestrator/skills/pipeline/nexus_daemon.py"

Write-Host "-> Starting Next.js Dashboard..."
Set-Location -Path "workspace-dashboard"
if (-Not (Test-Path "node_modules")) {
    Write-Host "-> Installing Dashboard dependencies (this will only happen once)..."
    npm install
}
Start-Process -NoNewWindow -FilePath "npm" -ArgumentList "run", "dev", "--", "-H", "0.0.0.0"
Set-Location -Path ".."

Write-Host "========================================="
Write-Host "Everything is LIVE! Press Ctrl+C to stop."
Write-Host "========================================="

# Keep the console open
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
}
catch {
    Write-Host "Stopping Hermes..."
    Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
    Stop-Process -Name "node" -Force -ErrorAction SilentlyContinue
}
