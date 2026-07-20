#!/bin/bash
echo "========================================="
echo "       STARTING HERMES ENGINE            "
echo "========================================="

echo "-> Cleaning up old background processes..."
pkill -f "telegram_router.py" 2>/dev/null || true
pkill -f "nexus_daemon.py" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
sleep 3

# Kill any zombie python processes holding the Telegram long-poll connection
kill $(lsof -ti:0 2>/dev/null) 2>/dev/null || true

# Force-clear Telegram's polling session before starting (avoids 409 Conflict)
echo "-> Clearing Telegram webhook/polling session..."
BOT_TOKEN=$(grep TELEGRAM_BOT_TOKEN workspace-bl-orchestrator/.env 2>/dev/null | cut -d'=' -f2 | tr -d '[:space:]')
if [ -n "$BOT_TOKEN" ]; then
    curl -s "https://api.telegram.org/bot${BOT_TOKEN}/deleteWebhook?drop_pending_updates=true" > /dev/null
    echo "   Telegram session cleared."
fi

sleep 2

# 1. Start the Telegram Bot Router in the background
echo "-> Starting Telegram Router (Bot Listener)..."
python workspace-bl-orchestrator/skills/pipeline/telegram_router.py &
ROUTER_PID=$!

# 2. Reset any failed leads and Start the Nexus Daemon (Hunter) in the background
echo "-> Resetting any failed leads..."
python reset_leads.py

echo "-> Starting Nexus Daemon (Hunter)..."
python workspace-bl-orchestrator/skills/pipeline/nexus_daemon.py &
DAEMON_PID=$!

# 3. Start the Next.js Dashboard
echo "-> Starting Next.js Dashboard..."
cd workspace-dashboard
if [ ! -d "node_modules" ]; then
    echo "-> Installing Dashboard dependencies (this will only happen once)..."
    npm install
fi
npm run dev -- -H 0.0.0.0 &
cd ..
DASHBOARD_PID=$!

echo "========================================="
echo "Everything is LIVE! Press Ctrl+C to stop."
echo "========================================="

# Trap Ctrl+C (SIGINT) so it cleanly kills all background processes when you exit
trap "echo 'Stopping Hermes...'; kill $ROUTER_PID $DAEMON_PID $DASHBOARD_PID 2>/dev/null; exit" INT

# Wait keeps the script running and printing logs to this terminal
wait
