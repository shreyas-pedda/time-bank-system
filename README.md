### Time Bank System
System which allows for peer-to-peer transactions to take place with the exchange of time credits and services instead of currency. Can be used for community building and enable people to socially support one another.

**Architecture Overview:**
The system consists of three microservices communicating via APIs:
1. User Profile Service: Create, manage, and authenticate users and their information

2. Exchange Service

* Create and update task requests with important details and time credit offers
* Task state management
* List current requests

3. Feedback Service: Allows users to leave reviews after requests are fullfilled

4. Nginx Service: Acts as a load balancer and API gateway. This means that Nginx is the single API entry point for all requests and also distributing network traffic across multiple instances of the services.

**Prerequisites:**
* Docker
* Git

**Installation & Setup:**

1. Clone the repository
```
git clone https://github.com/shreyas-pedda/time-bank-system.git
cd time-bank-system
```
2. Ensure project directory is correct. (Verify with structure below)

3. Build and Start Services

```
# Builds and starts all services
docker-compose up --build

# View logs, if necessary
docker-compose logs -f

# Verify all services are running correctly
docker-compose ps
```

**Project Structure:**

```
timebank-system/
├── docker-compose.yml
├── README.md
├── architecture_outline.md
├── ArchDiagram.drawio.png
├── user_profile_service/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       └── models.py
├── exchange_service/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       └── models.py
├── feedback_service/
│    ├── Dockerfile
│    ├── requirements.txt
│    └── app/
│        ├── __init__.py
│        ├── main.py
│        └── models.py
├── scripts/
│    ├── test_endpoints.sh
└── nginx/
    ├── Dockerfile
    ├── nginx.conf
```

**API Documentation:**

### User Profile Service (`/users/`)

#### Create User
- **Endpoint:** `POST /users`
- **Body:** `{ "name": "string", "email": "string", "description": "string (optional)" }`
- **Response:** User profile with initial 10 time credits
- **Example:** `curl -X POST http://localhost:8001/users -H "Content-Type: application/json" -d '{"name":"Alice","email":"alice@example.com"}'`

#### Get User
- **Endpoint:** `GET /users/{user_id}`
- **Response:** Full user profile
- **Example:** `curl http://localhost:8001/users/user_uuid`

#### Update User
- **Endpoint:** `PATCH /users/{user_id}`
- **Body:** `{ "name": "string (optional)", "description": "string (optional)" }`
- **Response:** Updated user profile

#### List Users
- **Endpoint:** `GET /users?limit=10&offset=0`
- **Response:** Array of user profiles
- **Example:** `curl http://localhost:8001/users`

#### Get User Balance
- **Endpoint:** `GET /users/{user_id}/balance`
- **Response:** `{ "id": "string", "time_credits": "int" }`
- **Example:** `curl http://localhost:8001/users/user_uuid/balance`

#### Transfer Credits
- **Endpoint:** `POST /users/transfer`
- **Body:** `{ "from_user_id": "string", "to_user_id": "string", "amount": "int" }`
- **Response:** `{ "from_user": UserBalance, "to_user": UserBalance }`
- **Note:** Validates sufficient balance, rejects negative amounts
- **Example:** `curl -X POST http://localhost:8001/users/transfer -H "Content-Type: application/json" -d '{"from_user_id":"uuid1","to_user_id":"uuid2","amount":5}'`

### Exchange Service (`/exchange/`)

#### Create Task
- **Endpoint:** `POST /tasks`
- **Body:** `{ "title": "string", "description": "string", "requested_by_user_id": "string", "time_credit_offer": "int" }`
- **Response:** Task response with state "open"
- **Validation:** Validates user exists, credit offer must be positive
- **Example:** `curl -X POST http://localhost:8002/tasks -H "Content-Type: application/json" -d '{"title":"Garden Setup","description":"Plant vegetables","requested_by_user_id":"uuid","time_credit_offer":5}'`

#### Get Task
- **Endpoint:** `GET /tasks/{task_id}`
- **Response:** Full task details
- **Example:** `curl http://localhost:8002/tasks/task_uuid`

#### List Tasks
- **Endpoint:** `GET /tasks?state=open&requested_by_user_id=uuid&accepted_by_user_id=uuid`
- **Query Params:**
  - `state`: Filter by state (open, pending, in_progress, completed, cancelled)
  - `requested_by_user_id`: Filter by creator
  - `accepted_by_user_id`: Filter by acceptor
- **Response:** Array of task responses
- **Example:** `curl http://localhost:8002/tasks?state=open`

#### Update Task
- **Endpoint:** `PATCH /tasks/{task_id}`
- **Body:** `{ "title": "string (optional)", "description": "string (optional)", "time_credit_offer": "int (optional)" }`
- **Restrictions:** Only available when task state is "open"

#### Accept Task (State: open → pending)
- **Endpoint:** `POST /tasks/{task_id}/accept`
- **Body:** `{ "acceptor_user_id": "string" }`
- **Response:** Updated task with state "pending"
- **Validation:** Validates acceptor exists, task must be open

#### Start Task (State: pending → in_progress)
- **Endpoint:** `POST /tasks/{task_id}/start`
- **Body:** `{ "started_by_user_id": "string" }`
- **Response:** Updated task with state "in_progress"
- **Restriction:** Only the acceptor can start the task

#### Complete Task (State: in_progress → completed)
- **Endpoint:** `POST /tasks/{task_id}/complete`
- **Body:** `{ "completed_by_user_id": "string" }`
- **Response:** Updated task with state "completed"
- **Behavior:**
  - Validates task is in_progress and completed by acceptor
  - Transfers time credits from requester to acceptor
  - Returns 400 if insufficient credits
- **Restriction:** Only the acceptor can complete the task

#### Cancel Task (State: open/pending → cancelled)
- **Endpoint:** `POST /tasks/{task_id}/cancel`
- **Body:** `{ "cancelled_by_user_id": "string", "reason": "string (optional)" }`
- **Response:** Updated task with state "cancelled"
- **Restriction:** Only the task creator can cancel, and only while task is open or pending

**Task States:**
- `open`: Task posted, waiting for someone to accept
- `pending`: Someone accepted the task, waiting to start
- `in_progress`: Task has been started
- `completed`: Task completed, credits transferred
- `cancelled`: Task cancelled by creator

**Testing:**
Run the comprehensive test script:
```
bash scripts/test_endpoints.sh
```

This tests user creation, task lifecycle, credit transfers, and error scenarios.

**Health Endpoints:**

```
curl http://localhost/health              # API Gateway

curl http://localhost:8001/health         # User Profile Service

curl http://localhost:8002/health         # Exchange Service

curl http://localhost:8003/health         # Feedback Service
```
