#!/bin/bash
echo "========================================="
echo "       🚀 STARTING HERMES ENGINE 🚀      "
echo "========================================="

# 1. Start the Telegram Bot Router in the background
echo "-> Starting Telegram Router (Bot Listener)..."
python workspace-bl-orchestrator/skills/pipeline/telegram_router.py &
ROUTER_PID=$!

# 2. Start the Nexus Daemon (Hunter) in the background
echo "-> Starting Nexus Daemon (Hunter)..."
python workspace-bl-orchestrator/skills/pipeline/nexus_daemon.py &
DAEMON_PID=$!

echo "========================================="
echo "✅ Both engines are LIVE! Press Ctrl+C to stop."
echo "========================================="

# Trap Ctrl+C (SIGINT) so it cleanly kills both background processes when you exit
trap "echo '🛑 Stopping Hermes Engines...'; kill $ROUTER_PID $DAEMON_PID; exit" INT

# Wait keeps the script running and printing logs to this terminal
wait
