#!/bin/bash
echo "========================================="
echo "       🚀 STARTING HERMES ENGINE 🚀      "
echo "========================================="

echo "-> Cleaning up old background processes..."
pkill -f "telegram_router.py" || true
pkill -f "nexus_daemon.py" || true
sleep 1

# 1. Start the Telegram Bot Router in the background
echo "-> Starting Telegram Router (Bot Listener)..."
python workspace-bl-orchestrator/skills/pipeline/telegram_router.py &
ROUTER_PID=$!

# 2. Start the Nexus Daemon (Hunter) in the background
echo "-> Starting Nexus Daemon (Hunter)..."
python workspace-bl-orchestrator/skills/pipeline/nexus_daemon.py &
DAEMON_PID=$!

# 3. Start the Next.js Dashboard
echo "-> Starting Next.js Dashboard..."
cd workspace-dashboard && npm run dev &
DASHBOARD_PID=$!

echo "========================================="
echo "✅ Everything is LIVE (Frontend + Backend)! Press Ctrl+C to stop."
echo "========================================="

# Trap Ctrl+C (SIGINT) so it cleanly kills all background processes when you exit
trap "echo '🛑 Stopping Hermes Engines and Dashboard...'; kill $ROUTER_PID $DAEMON_PID $DASHBOARD_PID; exit" INT

# Wait keeps the script running and printing logs to this terminal
wait
