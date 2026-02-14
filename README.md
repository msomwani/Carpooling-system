
# 🚗 Carpooling System 

A production-inspired, modular monolith backend for a carpooling platform.

This project focuses on **correctness, concurrency safety, and reliable distributed workflows** — not just CRUD endpoints.

---

# 🎯 Project Goal


- Strong transactional guarantees  
- Concurrency-safe booking logic  
- Idempotent API design  
- Event-driven architecture  
- Reliable event delivery via Outbox Pattern  
- Failure-aware system design  


---

# 🏗️ Architecture Overview

## Architecture Style: Modular Monolith

Chosen for:

- Clear domain boundaries  
- Strong ACID guarantees  
- Operational simplicity  
- Evolution path toward microservices  

---

## 🧭 Architecture Diagram

(docs/architecture/01_system_overview.png)

```

[ Client ]
     ↓
[ FastAPI Application ]
     ↓
[ PostgreSQL ]  ← Source of Truth
     ↓
[ Outbox Table ]
     ↓
[ Outbox Worker ]
     ↓
[ Kafka ]
     ↓
[ Consumers ]

```

---

# 🧠 Core Design Philosophy

### 🗄 PostgreSQL = Source of Truth
All critical business logic executes inside ACID transactions.

### ⚡ Redis = Performance Layer
Used strictly for read-through caching and performance optimization.

### 📡 Kafka = Asynchronous Side Effects
Used to decouple side effects (notifications, analytics, future extensions) from core booking transactions.

### 🧱 Outbox Pattern = Guaranteed Event Delivery
Events are written inside the DB transaction and later published by a background worker — eliminating silent event loss.

### 🔐 JWT = Stateless Authentication
Secure HTTP-only cookie-based authentication.

---

# 🧩 System Modules

```
app/
├── auth/        → Authentication & JWT
├── users/       → User management
├── rides/       → Ride creation & search
├── bookings/    → Booking lifecycle & idempotency
├── outbox/      → Durable event storage
├── common/      → DB, Redis, Kafka utilities
├── config/      → Environment configuration

workers/
├── outbox_processor.py
├── booking_consumer.py
```

---

# ✅ Implemented Features

## 🔐 Authentication
- Signup & login  
- Password hashing  
- JWT-based sessions  
- HTTP-only cookies  
- Protected endpoints via dependency injection  

## 🚗 Ride Management
- Drivers create rides  
- Passengers search rides  
- Indexed DB queries  
- Redis-backed caching  

## 🪑 Transaction-Safe Booking
- ACID transactions  
- `SELECT FOR UPDATE` row-level locking  
- Prevents overbooking under concurrency  
- O(1) seat updates with safe locking  

## 🔁 Idempotent Booking APIs
- Unique idempotency keys  
- Concurrency-safe insert handling  
- Safe retries  
- DB-level uniqueness constraints  

## 🔄 Booking Cancellation
- Transactional seat restoration  
- Compensating event emission  
- Event consistency maintained  

## 📡 Kafka Event System

Events:
- `booking.confirmed`
- `booking.cancelled`
- `booking.dlq`

Includes:
- Producer retries  
- Delivery confirmation callbacks  
- Consumer retry strategy  
- Dead Letter Queue  

## 🧱 Outbox Reliability Layer

Guarantees:
- If DB commits, event will eventually be delivered  
- No silent event loss  
- Crash-safe publishing  
- Durable event storage  

---

# 🧨 Failure Handling

- App crash during transaction → automatic rollback  
- Duplicate booking request → prevented via idempotency key  
- Kafka failure → retried via outbox processor  
- Consumer failure → retried with DLQ fallback  

---

# 🚀 Local Setup

## Start Infrastructure

```bash
docker-compose up -d
```

Starts:
- PostgreSQL
- Redis
- Kafka
- Zookeeper

## Run Backend

```bash
uvicorn app.main:app --reload
```

API docs:
http://127.0.0.1:8000/docs

## Run Outbox Worker

```bash
python workers/outbox_processor.py
```

---

# 📊 System Workflow

1️⃣ User authenticates  
2️⃣ Driver creates ride  
3️⃣ Passenger searches ride  
4️⃣ Passenger books ride (transaction-safe)  
5️⃣ Outbox event written inside transaction  
6️⃣ Worker publishes Kafka event  
7️⃣ Passenger cancels booking  
8️⃣ Compensating event processed  

---

# ❌ Non-Goals (Intentionally Excluded)

- No microservices (modular monolith by design)  
- No payment processing (future extension)  
- No distributed tracing (planned observability layer)  

---

# 🔜 Roadmap

## Observability
- Structured logging  
- Correlation IDs  
- Request tracing  

## Testing
- Unit tests  
- Integration tests  
- Concurrency stress tests  

## Operational Hardening
- Rate limiting  
- Health checks  
- Metrics endpoint  

## Feature Expansion
- Driver ride cancellation cascade  
- Messaging system  
- Payment integration  
- Analytics dashboard  
