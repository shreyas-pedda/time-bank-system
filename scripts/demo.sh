#!/bin/bash

# Time-Bank System Demo Script
# Demonstrates the complete workflow: user creation, task creation, acceptance, completion, and credit transfer

set -e

GATEWAY="http://localhost"
USERS_API="http://localhost:8001"
EXCHANGE_API="http://localhost:8002"

echo "=============================================="
echo "   Time-Bank System Demo"
echo "=============================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Helper function to extract ID from JSON response
extract_id() {
    echo "$1" | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4
}

echo -e "${BLUE}[Step 0] Health Checks${NC}"
echo "Checking all services..."

curl -s "$GATEWAY/health" > /dev/null && echo -e "${GREEN}✓${NC} Gateway health OK" || echo "✗ Gateway health check failed"
curl -s "$USERS_API/health" > /dev/null && echo -e "${GREEN}✓${NC} User service health OK" || echo "✗ User service health check failed"
curl -s "$EXCHANGE_API/health" > /dev/null && echo -e "${GREEN}✓${NC} Exchange service health OK" || echo "✗ Exchange service health check failed"

echo ""
echo -e "${BLUE}[Step 1] Creating Users${NC}"
echo "Creating Alice (task requester)..."

ALICE_RESPONSE=$(curl -s -X POST "$USERS_API/users" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice",
    "email": "alice@example.com",
    "description": "Task requester"
  }')

UUID_ALICE=$(extract_id "$ALICE_RESPONSE")
echo -e "${GREEN}✓${NC} Alice created with ID: $UUID_ALICE"

echo "Creating Bob (task helper)..."

BOB_RESPONSE=$(curl -s -X POST "$USERS_API/users" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Bob",
    "email": "bob@example.com",
    "description": "Task helper"
  }')

UUID_BOB=$(extract_id "$BOB_RESPONSE")
echo -e "${GREEN}✓${NC} Bob created with ID: $UUID_BOB"

echo ""
echo -e "${BLUE}[Step 2] Creating a Task${NC}"
echo "Creating 'Help with garden' task (3 credits)..."

TASK_RESPONSE=$(curl -s -X POST "$EXCHANGE_API/tasks" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"Help with garden\",
    \"description\": \"Plant vegetables and flowers\",
    \"requested_by_user_id\": \"$UUID_ALICE\",
    \"time_credit_offer\": 3
  }")

UUID_TASK=$(extract_id "$TASK_RESPONSE")
echo -e "${GREEN}✓${NC} Task created with ID: $UUID_TASK"

echo ""
echo -e "${BLUE}[Step 3] Bob Accepts the Task${NC}"
echo "Accepting task..."

ACCEPT_RESPONSE=$(curl -s -X POST "$EXCHANGE_API/tasks/$UUID_TASK/accept" \
  -H "Content-Type: application/json" \
  -d "{
    \"acceptor_user_id\": \"$UUID_BOB\"
  }")

echo -e "${GREEN}✓${NC} Task accepted by Bob"
echo "Task state: $(echo "$ACCEPT_RESPONSE" | grep -o '"state":"[^"]*' | cut -d'"' -f4)"

echo ""
echo -e "${BLUE}[Step 4] Bob Starts the Task${NC}"
echo "Starting task..."

START_RESPONSE=$(curl -s -X POST "$EXCHANGE_API/tasks/$UUID_TASK/start" \
  -H "Content-Type: application/json" \
  -d "{
    \"started_by_user_id\": \"$UUID_BOB\"
  }")

echo -e "${GREEN}✓${NC} Task started"
echo "Task state: $(echo "$START_RESPONSE" | grep -o '"state":"[^"]*' | cut -d'"' -f4)"

echo ""
echo -e "${BLUE}[Step 5] Bob Completes the Task${NC}"
echo "Completing task and transferring credits..."

COMPLETE_RESPONSE=$(curl -s -X POST "$EXCHANGE_API/tasks/$UUID_TASK/complete" \
  -H "Content-Type: application/json" \
  -d "{
    \"completed_by_user_id\": \"$UUID_BOB\"
  }")

echo -e "${GREEN}✓${NC} Task completed"
echo "Task state: $(echo "$COMPLETE_RESPONSE" | grep -o '"state":"[^"]*' | cut -d'"' -f4)"

echo ""
echo -e "${BLUE}[Step 6] Checking Final Balances${NC}"
echo "Retrieving balances..."

ALICE_BALANCE=$(curl -s "$USERS_API/users/$UUID_ALICE/balance")
BOB_BALANCE=$(curl -s "$USERS_API/users/$UUID_BOB/balance")

echo ""
echo -e "${YELLOW}Results:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "Alice: ${GREEN}$ALICE_BALANCE${NC}"
echo -e "Bob:   ${GREEN}$BOB_BALANCE${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo -e "${BLUE}[Step 7] Verifying Task History${NC}"
echo "Retrieving task details..."

TASK_DETAIL=$(curl -s "$EXCHANGE_API/tasks/$UUID_TASK")
echo "Task title: $(echo "$TASK_DETAIL" | grep -o '"title":"[^"]*' | cut -d'"' -f4)"
echo "Task state: $(echo "$TASK_DETAIL" | grep -o '"state":"[^"]*' | cut -d'"' -f4)"
echo "Requester:  $(echo "$TASK_DETAIL" | grep -o '"requested_by_user_id":"[^"]*' | cut -d'"' -f4)"
echo "Acceptor:   $(echo "$TASK_DETAIL" | grep -o '"accepted_by_user_id":"[^"]*' | cut -d'"' -f4)"

echo ""
echo "=============================================="
echo "   Demo Complete!"
echo "=============================================="
echo ""
echo "Summary:"
echo "  • Created 2 users (Alice and Bob)"
echo "  • Created 1 task for 3 credits"
echo "  • Bob accepted and completed the task"
echo "  • Credits transferred: Alice -3, Bob +3"
echo ""
echo "IDs for reference:"
echo "  Alice ID: $UUID_ALICE"
echo "  Bob ID:   $UUID_BOB"
echo "  Task ID:  $UUID_TASK"
echo ""
