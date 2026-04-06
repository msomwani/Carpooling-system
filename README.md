<div align="center">
  <h1>🐊 Croc Ride</h1>
  <p>A Correctness-First, Community-Driven Carpooling Platform focused on the Vadodara-Halol Corridor.</p>
</div>

---

<details>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#about-the-project">About The Project</a></li>
    <li><a href="#key-features">Key Features</a></li>
    <li><a href="#system-architecture">System Architecture</a></li>
    <li><a href="#getting-started">Getting Started</a></li>
    <li><a href="#project-structure">Project Structure</a></li>
    <li><a href="#development-roadmap">Development Roadmap</a></li>
  </ol>
</details>

## About The Project

**Croc Ride** is a dedicated carpooling application built specifically for repeat, daily commuters traveling along the high-traffic Vadodara (Baroda) to Halol corridor. 

Unlike traditional taxi-hailing applications that optimize for instantaneous ad-hoc trips, Croc Ride is designed around **cost-sharing and community trust**. Our goal is to connect individuals driving empty cars with passengers heading precisely on their route. 

The system started as an experimental concept to handle advanced **Geospatial routing** and **High-Concurrency Seat Booking** safely, and has since matured into a production-inspired, containerized platform.

## Key Features

- 📍 **Advanced Spatial Search**: Instead of just matching pickup-to-pickup, the system maps the driver's exact journey as a continuous geometric line (`LineString`) and matches passengers standing anywhere along that route.
- 🚦 **Smart Corridor Geocoding**: Native support for searching colloquial route landmarks (e.g., "Airport", "Station") which are converted instantly into exact geospatial coordinates.
- 🚗 **Multi-Vehicle Management**: Drivers can maintain a virtual garage of their vehicles and toggle between them prior to creating shared rides.
- 🔒 **Race-Condition-Proof Bookings**: Relying deeply on PostgreSQL's row-level locking (`SELECT FOR UPDATE`), the platform guarantees that in a split-second race between 10 passengers for 1 remaining seat, exactly one person gets the booking without data corruption.
- 🛡️ **Frictionless Google OAuth**: Clean, spam-free onboarding configured exclusively through `@react-oauth/google` with strict, stateless backend cookie session validation.

## System Architecture

We employ a **Modular Monolith** architecture. While microservices offer scaling patterns, keeping domains bound in a single codebase with clean folder separation achieves immense developer velocity while preserving strict transactional ACID guarantees.

- **Frontend Web**: Next.js (App Router), Tailwind CSS, Leaflet Maps, OSRM Routing.
- **Backend Core**: Python, FastAPI.
- **Source of Truth**: PostgreSQL + PostGIS (Mandatory for our geometric routing math).
- **Speed Layer**: Redis (Caching frequent searches and tracking driver locations).
- **Asynchronous Reliability**: Apache Kafka.
- **The Delivery Guarantee**: We utilize the **Outbox Pattern**. Booking events are written into an `outbox_events` table in the exact same database transaction as the booking itself. A background worker picks this up to fire off to Kafka. This guarantees we never lose an event if external services drop temporarily.

## Getting Started

Because of our reliance on Kafka, Redis, and PostGIS, the easiest way to run the platform locally is via Docker.

### Prerequisites
- Docker & Docker Compose Desktop

### Local Installation

1. **Configure Environment Variables**
   Create a `.env` in the root directory referencing your API Keys:
   ```env
   GOOGLE_CLIENT_ID=your_google_oauth_client_id
   JWT_SECRET=your_strong_secret
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   POSTGRES_DB=carpool_db
   ```

2. **Spin Up the Infra**
   Deploy the entire 9-container stack (Database, Cache, Message Brokers, Event Workers, APIs, and Frontend) in one command:
   ```bash
   docker compose up -d --build
   ```

3. **Access the App**
   - **Frontend App:** [http://localhost:3000](http://localhost:3000)
   - **Backend Server / API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

## Project Structure

```text
Croc Ride/
├── backend/                  # FastAPI Application
│   ├── app/
│   │   ├── users/            # Profiles, Vehicles, Role Hierarchy
│   │   ├── rides/            # Ride Creation & Geospatial Algorithms
│   │   ├── bookings/         # Transaction-safe seat reservations
│   │   ├── auth/             # Google OAuth & JWT handler APIs
│   │   └── workers/          # Background Kafka Workers (Outbox Polling)
│   └── ...
├── carpool-frontend/         # Next.js Application
│   ├── app/                  # Next.js Server Components & Pages
│   ├── components/           # Reusable UI (Leaflet Maps, Shadcn) 
│   └── lib/                  # AuthContext Providers and fetchers
└── docker-compose.yml        # Docker orchestration configuration
```

## Development Roadmap

Croc Ride is fully operational from an algorithmic routing and booking standpoint, but is continuously improving towards a public release. The current developmental roadmap distinguishes between what is functional and what is queued up:

**✅ Fully Implemented & Functioning:**
- Stateless JWT Authorization via Google.
- OSRM Polyline generation & Advanced PostGIS `ST_DWithin` spatial ride matching.
- Concurrency-safe seat allocation & complex cascading cancellations.
- `slowapi` rate limiting across dangerous endpoints.
- Fully dockerized `docker-compose` orchestration.

**⚙️ Payments (Test Mode Active):**
- **Razorpay Integration**: Our escrow payment gateway is successfully built and holding payments in **Test Mode**. It handles capturing funds and executing automated refunds during user cancellations. We are actively finalizing security audits before pushing it to a live production environment.

**🚧 In the Backlog / Pending:**
- **Trust & Verification**: Sprints are planned to implement Phone number OTPs, ID-Card Uploads, and mutual ratings to enforce safety.
- **Automated Alerts**: Transitioning Kafka events to trigger real-time WebSockets and cross-platform SMS (Twilio/MSG91) updates to notify users of ride status changes offline.
- **Infrastructure Scaling**: Adding production CI pipelines, securing CORS origins, and moving toward domain/SSL implementations.
