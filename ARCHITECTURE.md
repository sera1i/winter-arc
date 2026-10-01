# Architecture Decision Records (ADR)

## ADR 1: Modular Monolith vs Microservices
**Date:** 2026-10-01
**Decision:** We will build a modular monolith using Django.
**Rationale:** The application requires high operational cohesion around user data. Cross-user isolation and data integrity (e.g. XP idempotency, streak calculations) are simpler to enforce with transactions in a single RDBMS schema. Microservices would introduce unnecessary deployment complexity without immediate scale benefits.

## ADR 2: Django Templates vs SPA (React)
**Date:** 2026-10-01
**Decision:** We will use Django Templates + Vanilla JS (fetch) for interactive elements, but simultaneously expose a complete REST API using Django REST Framework (DRF).
**Rationale:** Using templates allows rapid iteration for MVP. The DRF API ensures that a React SPA or mobile client can be adopted later without rebuilding the backend logic.

## ADR 3: PostgreSQL Database
**Date:** 2026-10-01
**Decision:** Use PostgreSQL as the primary data store.
**Rationale:** The application has strict relational requirements (e.g. Goals -> Tasks -> Milestones) and requires transaction safety for habit completion and XP calculation.

## ADR 4: Background Jobs & Notifications
**Date:** 2026-10-01
**Decision:** Use Celery with Redis broker.
**Rationale:** The app requires reliable scheduling for habit/task reminders, asynchronous metric aggregation, and robust retry logic, which Celery provides natively.

