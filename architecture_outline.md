**System Purpose:** A peer-to-peer platform where users in communities can exchange services for time credits instead of monetary currency. Each user can create their own profiles, request services, or complete other users' requests.

**Service Boundaries:** Explanation of each service's responsibility and why services are separated the way they are

1. User Service
* User account creation & authentication
* Manage user profile: description, amount of time credits, skills
* Log of user history including previously created tasks, tasks which a user has completed, and any feedback received on each of those

2. Exchange Service
* Each user can respectively create or update the tasks which they request. Each request stores important details, amount of time credit offered, state (pending/accepted/completed)
* List all tasks in the catalog which have been requested at the moment
* Once tasks are completed, updates the amount of time credits in each of the corresponding user profiles

3. Feedback Service
* Allows both request creators and completers to leave reviews once done
* Stores all of the feedback instances
* Querying for reviews on certain user profiles

**Data Flow:** Description of how health check information flows through your system

*Full Core Workflow*
1. User Creation
   User → User Profile Service → Redis

2. Task Creation
   Creator → Exchange Service → Validate Creator (User Service) → Redis

3. Task Acceptance
   Acceptor → Exchange Service → Validate Acceptor (User Service) → Update Task → Redis

4. Task Completion
   Acceptor → Exchange Service → Transfer Credits (User Service) → Update History → Redis

5. Feedback Submission
   User → Feedback Service → Validate Task (Exchange Service) → Validate Users (User Service) → Redis

<!-- **Communication Patterns:**  -->

**Technology Stack:**
- FastAPI: Supports Service API endpoints
- Redis: Main database storage
- Docker & Compose: Manage containers and services
- httpx: For communication between services
- Pydantic: Data validation, type safety
