#!/bin/bash
# -----------------------------------------------------------------------------
# 🧠 NSA ReflexArc — Supervisor Restart Script
# -----------------------------------------------------------------------------
# This script runs ReflexArc and monitors its exit code.
# If the application crashes (non-zero exit code), it will automatically 
# self-heal and restart it after an exponential backoff.
# -----------------------------------------------------------------------------

MAX_RESTARTS=10
RESTART_DELAY=2  # Initial delay in seconds
RESTART_COUNT=0

# ANSI color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}🧠 Starting NSA ReflexArc Supervisor Mode${NC}"
echo -e "${BLUE}======================================================${NC}"

while true; do
    echo -e "${GREEN}[$(date +'%H:%M:%S')] Starting python main.py...${NC}"
    
    # Run the application (pass along any command line arguments)
    python main.py "$@"
    EXIT_CODE=$?
    
    # Check exit code
    if [ $EXIT_CODE -eq 0 ]; then
        echo -e "${GREEN}[$(date +'%H:%M:%S')] ReflexArc exited cleanly. Supervisor shutting down.${NC}"
        exit 0
    fi
    
    echo -e "${RED}[$(date +'%H:%M:%S')] ReflexArc crashed with exit code $EXIT_CODE.${NC}"
    
    # Check if we've exceeded max restarts
    RESTART_COUNT=$((RESTART_COUNT + 1))
    if [ $RESTART_COUNT -gt $MAX_RESTARTS ]; then
        echo -e "${RED}FATAL: Exceeded maximum restart count ($MAX_RESTARTS). Shutting down supervisor.${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Auto-restarting in $RESTART_DELAY seconds (Attempt $RESTART_COUNT/$MAX_RESTARTS)...${NC}"
    sleep $RESTART_DELAY
    
    # Exponential backoff (max 60 seconds)
    RESTART_DELAY=$((RESTART_DELAY * 2))
    if [ $RESTART_DELAY -gt 60 ]; then
        RESTART_DELAY=60
    fi
done
