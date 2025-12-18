#!/usr/bin/env bash
set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

GATEWAY="http://localhost"
USERS_API="http://localhost:8001"
EXCHANGE_API="http://localhost:8002"

echo -e "${YELLOW}=== Time Bank System Endpoint Tests ===${NC}\n"

# Test 1: Health checks
echo -e "${YELLOW}Test 1: Health Checks${NC}"
curl -s "$GATEWAY/health" | jq . && echo -e "${GREEN}✓ Gateway health${NC}" || echo -e "${RED}✗ Gateway health${NC}"
curl -s "$USERS_API/health" | jq . && echo -e "${GREEN}✓ User service health${NC}" || echo -e "${RED}✗ User service health${NC}"
curl -s "$EXCHANGE_API/health" | jq . && echo -e "${GREEN}✓ Exchange service health${NC}" || echo -e "${RED}✗ Exchange service health${NC}"

# Test 2: Create users
echo -e "\n${YELLOW}Test 2: Create Users${NC}"
USER1=$(curl -s -X POST "$USERS_API/users" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice",
    "email": "alice@example.com",
    "description": "Gardening expert"
  }' | jq -r '.id')
echo -e "${GREEN}✓ Created User 1 (Alice): $USER1${NC}"

USER2=$(curl -s -X POST "$USERS_API/users" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Bob",
    "email": "bob@example.com",
    "description": "Handyman"
  }' | jq -r '.id')
echo -e "${GREEN}✓ Created User 2 (Bob): $USER2${NC}"

# Test 3: Get user details
echo -e "\n${YELLOW}Test 3: Get User Details${NC}"
curl -s "$USERS_API/users/$USER1" | jq . && echo -e "${GREEN}✓ Get user $USER1${NC}"

# Test 4: List users
echo -e "\n${YELLOW}Test 4: List Users${NC}"
curl -s "$USERS_API/users" | jq . && echo -e "${GREEN}✓ List all users${NC}"

# Test 5: Get user balance
echo -e "\n${YELLOW}Test 5: Get User Balance${NC}"
curl -s "$USERS_API/users/$USER1/balance" | jq . && echo -e "${GREEN}✓ Get balance for $USER1${NC}"

# Test 6: Create task
echo -e "\n${YELLOW}Test 6: Create Task (Alice posts gardening task)${NC}"
TASK1=$(curl -s -X POST "$EXCHANGE_API/tasks" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"Garden Setup\",
    \"description\": \"Plant a vegetable garden\",
    \"requested_by_user_id\": \"$USER1\",
    \"time_credit_offer\": 5
  }" | jq -r '.id')
echo -e "${GREEN}✓ Created Task 1: $TASK1${NC}"

# Test 7: Get task
echo -e "\n${YELLOW}Test 7: Get Task Details${NC}"
curl -s "$EXCHANGE_API/tasks/$TASK1" | jq . && echo -e "${GREEN}✓ Get task $TASK1${NC}"

# Test 8: List tasks
echo -e "\n${YELLOW}Test 8: List All Tasks${NC}"
curl -s "$EXCHANGE_API/tasks" | jq . && echo -e "${GREEN}✓ List all tasks${NC}"

# Test 9: Accept task
echo -e "\n${YELLOW}Test 9: Accept Task (Bob accepts Alice's task)${NC}"
curl -s -X POST "$EXCHANGE_API/tasks/$TASK1/accept" \
  -H "Content-Type: application/json" \
  -d "{\"acceptor_user_id\": \"$USER2\"}" | jq . && echo -e "${GREEN}✓ Bob accepted task${NC}"

# Test 10: Start task
echo -e "\n${YELLOW}Test 10: Start Task${NC}"
curl -s -X POST "$EXCHANGE_API/tasks/$TASK1/start" \
  -H "Content-Type: application/json" \
  -d "{\"started_by_user_id\": \"$USER2\"}" | jq . && echo -e "${GREEN}✓ Bob started task${NC}"

# Test 11: Complete task and transfer credits
echo -e "\n${YELLOW}Test 11: Complete Task (Transfer Credits)${NC}"
curl -s -X POST "$EXCHANGE_API/tasks/$TASK1/complete" \
  -H "Content-Type: application/json" \
  -d "{\"completed_by_user_id\": \"$USER2\"}" | jq . && echo -e "${GREEN}✓ Task completed, credits transferred${NC}"

# Test 12: Verify balances after transfer
echo -e "\n${YELLOW}Test 12: Verify Balances After Transfer${NC}"
echo "Alice's balance:"
curl -s "$USERS_API/users/$USER1/balance" | jq .
echo "Bob's balance:"
curl -s "$USERS_API/users/$USER2/balance" | jq .

# Test 13: Filter tasks by state
echo -e "\n${YELLOW}Test 13: Filter Tasks by State${NC}"
curl -s "$EXCHANGE_API/tasks?state=completed" | jq . && echo -e "${GREEN}✓ Filter completed tasks${NC}"

# Test 14: Create another task and test cancel
echo -e "\n${YELLOW}Test 14: Create and Cancel Task${NC}"
TASK2=$(curl -s -X POST "$EXCHANGE_API/tasks" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"House Cleaning\",
    \"description\": \"Clean the house\",
    \"requested_by_user_id\": \"$USER2\",
    \"time_credit_offer\": 3
  }" | jq -r '.id')
echo -e "${GREEN}✓ Created Task 2: $TASK2${NC}"

curl -s -X POST "$EXCHANGE_API/tasks/$TASK2/cancel" \
  -H "Content-Type: application/json" \
  -d "{\"cancelled_by_user_id\": \"$USER2\"}" | jq . && echo -e "${GREEN}✓ Cancelled task${NC}"

# Test 15: Test insufficient balance error
echo -e "\n${YELLOW}Test 15: Test Insufficient Balance Error${NC}"
TASK3=$(curl -s -X POST "$EXCHANGE_API/tasks" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"Expensive Task\",
    \"description\": \"Very expensive\",
    \"requested_by_user_id\": \"$USER1\",
    \"time_credit_offer\": 100
  }" | jq -r '.id')
echo -e "${GREEN}✓ Created Task 3 (high cost): $TASK3${NC}"

curl -s -X POST "$EXCHANGE_API/tasks/$TASK3/accept" \
  -H "Content-Type: application/json" \
  -d "{\"acceptor_user_id\": \"$USER2\"}" | jq .
curl -s -X POST "$EXCHANGE_API/tasks/$TASK3/start" \
  -H "Content-Type: application/json" \
  -d "{\"started_by_user_id\": \"$USER2\"}" | jq .

echo "Attempting to complete task with insufficient credits..."
curl -s -X POST "$EXCHANGE_API/tasks/$TASK3/complete" \
  -H "Content-Type: application/json" \
  -d "{\"completed_by_user_id\": \"$USER2\"}" | jq . && echo -e "${RED}✗ Should have failed${NC}" || echo -e "${GREEN}✓ Correctly rejected due to insufficient credits${NC}"

echo -e "\n${YELLOW}=== All Tests Complete ===${NC}"
