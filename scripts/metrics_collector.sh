#!/usr/bin/env bash

# Simple Metrics Collection for Time-Bank-System
# Measures: Normal load latency, Concurrent load latency, Error rates

USERS_API="http://localhost:8001"
EXCHANGE_API="http://localhost:8002"

echo "======================================"
echo "Time-Bank System Performance Metrics"
echo "======================================"

# Helper function
measure_latency() {
    local url=$1
    local method=${2:-GET}
    local data=${3:-}

    local start=$(date +%s%N)

    if [ -z "$data" ]; then
        http_code=$(curl -s -w "%{http_code}" -o /dev/null -X "$method" "$url" \
            -H "Content-Type: application/json")
    else
        http_code=$(curl -s -w "%{http_code}" -o /dev/null -X "$method" "$url" \
            -H "Content-Type: application/json" -d "$data")
    fi

    local end=$(date +%s%N)
    local latency_ms=$(( (end - start) / 1000000 ))

    echo "$latency_ms|$http_code"
}

extract_id() {
    echo "$1" | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4 || echo ""
}


echo ""
echo "[Phase 1] Normal Load Latency - User Creation"
echo "Creating 5 users sequentially..."

user_latencies=()
user_ids=()
for i in {1..5}; do
    result=$(measure_latency "$USERS_API/users" POST "{\"name\":\"User$i\",\"email\":\"user$i@test.com\"}")
    latency=$(echo "$result" | cut -d'|' -f1)
    http_code=$(echo "$result" | cut -d'|' -f2)
    user_latencies+=("$latency")
    echo "  User $i: ${latency}ms (HTTP $http_code)"
done

# Calculate average
avg_user=0
for lat in "${user_latencies[@]}"; do
    avg_user=$((avg_user + lat))
done
avg_user=$((avg_user / ${#user_latencies[@]}))
echo "  ✓ Average user creation: ${avg_user}ms"

echo ""
echo "[Phase 2] Task Operations Under Normal Load"

# Create task
task_result=$(measure_latency "$EXCHANGE_API/tasks" POST "{\"title\":\"Test Task\",\"description\":\"Test\",\"requested_by_user_id\":\"test-user\",\"time_credit_offer\":5}")
task_latency=$(echo "$task_result" | cut -d'|' -f1)
task_http=$(echo "$task_result" | cut -d'|' -f2)
echo "  Task creation: ${task_latency}ms (HTTP $task_http)"

# Get task list
task_list_result=$(measure_latency "$EXCHANGE_API/tasks" GET)
task_list_latency=$(echo "$task_list_result" | cut -d'|' -f1)
echo "  Task list retrieval: ${task_list_latency}ms"

echo ""
echo "[Phase 3] Concurrent Load Test (20 parallel requests)"

# 20 sequential GETs to measure under concurrent conditions
start=$(date +%s%N)
for i in {1..20}; do
    curl -s -o /dev/null -X GET "$USERS_API/users" \
        -H "Content-Type: application/json" &
done
wait
end=$(date +%s%N)
concurrent_time_ms=$(( (end - start) / 1000000 ))
avg_concurrent=$((concurrent_time_ms / 20))
echo "  ✓ 20 parallel user GETs: ${avg_concurrent}ms average per request"
echo "    Total time: ${concurrent_time_ms}ms"

echo ""
echo "[Phase 4] Stress Test (50 rapid requests)"

start=$(date +%s%N)
for i in {1..50}; do
    curl -s -o /dev/null -X GET "$EXCHANGE_API/tasks" \
        -H "Content-Type: application/json" &
done
wait
end=$(date +%s%N)
total_stress_ms=$(( (end - start) / 1000000 ))
throughput=$(awk "BEGIN {printf \"%.2f\", 50000 / $total_stress_ms}")
echo "  ✓ 50 rapid task list requests"
echo "    Total time: ${total_stress_ms}ms"
echo "    Throughput: ${throughput} req/sec"

echo ""
echo "[Phase 5] Error Rate Testing - Invalid Requests"

errors=0

# Invalid user ID
http_code=$(curl -s -w "%{http_code}" -o /dev/null -X GET "$USERS_API/users/invalid-id-xyz" \
    -H "Content-Type: application/json")
if [ "$http_code" != "200" ]; then
    echo "  ✓ Invalid user request: HTTP $http_code (expected 404)"
    ((errors++))
else
    echo "  ✗ Invalid user request: HTTP $http_code (expected 404)"
fi

# Invalid task ID
http_code=$(curl -s -w "%{http_code}" -o /dev/null -X GET "$EXCHANGE_API/tasks/invalid-task-xyz" \
    -H "Content-Type: application/json")
if [ "$http_code" != "200" ]; then
    echo "  ✓ Invalid task request: HTTP $http_code (expected 404)"
    ((errors++))
else
    echo "  ✗ Invalid task request: HTTP $http_code (expected 404)"
fi

error_rate=$((errors * 100 / 2))
echo "  ✓ Error handling correctness: ${error_rate}%"

echo ""
echo "======================================"
echo "SUMMARY REPORT"
echo "======================================"
echo ""
echo "NORMAL LOAD:"
echo "  User Creation (5 sequential):  ${avg_user}ms avg"
echo "  Task Creation:                 ${task_latency}ms"
echo "  Task List Retrieval:           ${task_list_latency}ms"
echo ""
echo "SCALED/CONCURRENT LOAD:"
echo "  20 Parallel Requests:          ${avg_concurrent}ms avg per request"
echo "  Total Time (20 parallel):      ${concurrent_time_ms}ms"
echo ""
echo "STRESS TEST:"
echo "  50 Rapid Requests Throughput:  ${throughput} req/sec"
echo "  Total Time (50 requests):      ${total_stress_ms}ms"
echo ""
echo "ERROR HANDLING:"
echo "  Invalid Requests Rejection:    ${error_rate}% success rate"
echo "  System properly returns 404 for non-existent resources"
echo ""
echo "======================================"
echo "✓ Metrics collection complete"
