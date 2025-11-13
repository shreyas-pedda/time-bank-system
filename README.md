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

<!-- **Usage Instructions:** How to check health of your services (example curl commands or API endpoints) -->

**API Documentation:** List of all health endpoints with request/response examples

```curl http://localhost:8001/health``` -> tests health of the user_profile_service

```curl http://localhost:8002/health``` -> tests health of the exchange_service

```curl http://localhost:8003/health``` -> tests health of the feedback_service

**Testing:** Currently, manual testing of services is provided through the health endpoints.

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
└── feedback_service/
    ├── Dockerfile
    ├── requirements.txt
    └── app/
        ├── __init__.py
        ├── main.py
        └── models.py
```
