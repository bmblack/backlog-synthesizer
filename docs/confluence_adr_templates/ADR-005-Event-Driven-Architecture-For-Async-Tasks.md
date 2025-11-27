# ADR-005: Event-Driven Architecture for Asynchronous Tasks

**Status**: Accepted
**Date**: 2024-02-10
**Decision Makers**: Architecture Team, DevOps Lead
**Tags**: architecture, async, events, messaging

---

## Context

We need to handle long-running operations (email notifications, report generation, data processing) without blocking API requests. These operations:
- Take >3 seconds to complete
- May fail and need retries
- Should not block user requests
- Need to scale independently

## Decision

**We will adopt an event-driven architecture** using Redis as our message broker for asynchronous task processing.

**Components**:
- **Producer**: API servers emit events when async work is needed
- **Message Broker**: Redis Pub/Sub + Redis Streams
- **Consumer**: Background workers process events
- **Dead Letter Queue**: Failed events moved to DLQ after 3 retries

**Not using**: RabbitMQ, Apache Kafka, AWS SQS (for now)

## Architecture

```
┌─────────────┐       Event        ┌─────────────┐
│   API       │──────publish────────▶│   Redis    │
│  Server     │                      │  Streams   │
└─────────────┘                      └─────────────┘
                                           │
                                     subscribe
                                           │
                                           ▼
                                    ┌─────────────┐
                                    │  Background │
                                    │   Worker    │
                                    └─────────────┘
                                           │
                                    ┌──────┴──────┐
                                    │             │
                                Success        Failure
                                    │             │
                                    ▼             ▼
                             ┌──────────┐  ┌──────────┐
                             │  Audit   │  │   Dead   │
                             │   Log    │  │  Letter  │
                             └──────────┘  │  Queue   │
                                           └──────────┘
```

## Event Schema

**Standard Event Format**:
```json
{
  "event_id": "evt_abc123",
  "event_type": "user.registered",
  "timestamp": "2024-02-10T10:30:00Z",
  "version": "1.0",
  "payload": {
    "user_id": "usr_xyz789",
    "email": "user@example.com"
  },
  "metadata": {
    "source": "api-server-01",
    "correlation_id": "req_def456",
    "retry_count": 0
  }
}
```

## Event Types

### User Events
- `user.registered` - New user account created
- `user.updated` - User profile modified
- `user.deleted` - User account deleted
- `user.password_reset` - Password reset requested

### Notification Events
- `notification.email` - Send email notification
- `notification.sms` - Send SMS notification
- `notification.push` - Send push notification

### Report Events
- `report.generate` - Generate PDF/CSV report
- `report.completed` - Report generation finished
- `report.failed` - Report generation failed

### Data Processing Events
- `data.import` - Bulk data import requested
- `data.export` - Bulk data export requested
- `data.sync` - Sync with external system

## Use Cases

### ✅ Use Event-Driven for:

1. **Email/SMS Notifications**
   - User registration emails
   - Password reset emails
   - Marketing campaigns
   - Transactional notifications

2. **Report Generation**
   - PDF reports (takes 10-30 seconds)
   - CSV exports (large datasets)
   - Analytics dashboards

3. **Data Processing**
   - Image resizing/optimization
   - Video transcoding
   - Bulk imports/exports
   - Data migration

4. **External API Calls**
   - Webhook deliveries
   - Third-party integrations
   - Payment processing callbacks

5. **Scheduled Tasks**
   - Daily report generation
   - Cleanup jobs
   - Cache warming
   - Data aggregation

### ❌ Do NOT use Event-Driven for:

1. **Synchronous Operations**
   - User login (needs immediate response)
   - Real-time validation
   - Data retrieval (GET requests)

2. **Critical Path Operations**
   - Payment authorization (user waits)
   - Order placement confirmation
   - Real-time inventory checks

3. **Simple Operations**
   - Database reads
   - Simple calculations (<100ms)
   - Cache lookups

## Implementation

### Producing Events (API Server)

```python
from redis import Redis
import json
from datetime import datetime
import uuid

class EventPublisher:
    def __init__(self):
        self.redis = Redis(host='localhost', port=6379)

    def publish(self, event_type: str, payload: dict) -> str:
        event = {
            "event_id": f"evt_{uuid.uuid4().hex[:12]}",
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "1.0",
            "payload": payload,
            "metadata": {
                "source": "api-server",
                "correlation_id": request.id,  # from request context
                "retry_count": 0
            }
        }

        # Publish to Redis Stream
        self.redis.xadd(
            name=f"events:{event_type}",
            fields={"data": json.dumps(event)}
        )

        return event["event_id"]

# Usage in API endpoint
@app.post("/users")
async def create_user(user: UserCreate):
    # Create user in database
    user = db.create_user(user)

    # Publish event (non-blocking)
    publisher = EventPublisher()
    publisher.publish("user.registered", {
        "user_id": user.id,
        "email": user.email
    })

    # Return immediately
    return {"id": user.id, "status": "created"}
```

### Consuming Events (Background Worker)

```python
from redis import Redis
import json
import logging

class EventConsumer:
    def __init__(self):
        self.redis = Redis(host='localhost', port=6379)
        self.handlers = {}

    def register_handler(self, event_type: str, handler):
        self.handlers[event_type] = handler

    def start(self):
        # Create consumer group
        try:
            self.redis.xgroup_create(
                name="events:*",
                groupname="workers",
                id="0",
                mkstream=True
            )
        except Exception:
            pass  # Group already exists

        while True:
            # Read events
            events = self.redis.xreadgroup(
                groupname="workers",
                consumername="worker-01",
                streams={"events:*": ">"},
                count=10,
                block=5000  # 5 second timeout
            )

            for stream, messages in events:
                for message_id, data in messages:
                    self._process_event(stream, message_id, data)

    def _process_event(self, stream, message_id, data):
        try:
            event = json.loads(data[b"data"])
            event_type = event["event_type"]

            if event_type in self.handlers:
                # Process event
                self.handlers[event_type](event["payload"])

                # Acknowledge success
                self.redis.xack(stream, "workers", message_id)

                logging.info(f"Processed event {event['event_id']}")
            else:
                logging.warning(f"No handler for {event_type}")

        except Exception as e:
            logging.error(f"Failed to process event: {e}")
            self._handle_failure(stream, message_id, event, e)

    def _handle_failure(self, stream, message_id, event, error):
        retry_count = event["metadata"]["retry_count"]

        if retry_count < 3:
            # Retry
            event["metadata"]["retry_count"] += 1
            self.redis.xadd(stream, {"data": json.dumps(event)})
            self.redis.xack(stream, "workers", message_id)
        else:
            # Move to Dead Letter Queue
            self.redis.xadd(
                "events:dlq",
                {"data": json.dumps({**event, "error": str(error)})}
            )
            self.redis.xack(stream, "workers", message_id)

# Usage
consumer = EventConsumer()

# Register handlers
@consumer.register_handler("user.registered")
def handle_user_registered(payload):
    user_id = payload["user_id"]
    email = payload["email"]

    # Send welcome email
    send_email(
        to=email,
        subject="Welcome!",
        template="welcome",
        context={"user_id": user_id}
    )

# Start consuming
consumer.start()
```

## Retry Strategy

**Policy**: Exponential backoff with max 3 retries

| Attempt | Delay | Total Time |
|---------|-------|------------|
| 1 (initial) | 0s | 0s |
| 2 (retry 1) | 5s | 5s |
| 3 (retry 2) | 15s | 20s |
| 4 (retry 3) | 45s | 65s |
| Failed → DLQ | - | - |

**After 3 failed retries**:
- Move event to Dead Letter Queue (DLQ)
- Log error with full context
- Alert on-call engineer (if critical)
- Manual intervention required

## Monitoring & Observability

**Metrics to Track**:
- Events published per second (by type)
- Events processed per second (by type)
- Processing latency (p50, p95, p99)
- Error rate per event type
- DLQ size (alert if > 100)
- Consumer lag (events pending processing)

**Alerting**:
- DLQ size > 100 events
- Consumer lag > 5 minutes
- Error rate > 5% for any event type
- Zero events processed in 10 minutes (worker down)

## Constraints

### MUST Follow:

**Event Production**:
- All async operations MUST publish events (not direct worker calls)
- Events MUST use standard schema (event_id, event_type, timestamp, payload, metadata)
- Event types MUST follow naming convention: `resource.action` (e.g., `user.created`)
- Events MUST include `correlation_id` for tracing

**Event Consumption**:
- Workers MUST acknowledge events after successful processing
- Workers MUST implement retry logic (max 3 attempts)
- Failed events MUST be moved to DLQ after max retries
- Workers MUST be idempotent (can safely process same event twice)

**Error Handling**:
- MUST NOT retry events with client errors (400, 401, 404)
- MUST retry events with transient errors (timeout, 500, network)
- MUST log all event processing attempts (success and failure)
- MUST NOT lose events (use acknowledgment)

### MUST NOT:

**Prohibited Practices**:
- MUST NOT use events for synchronous operations (user waits for result)
- MUST NOT publish events for simple operations (<100ms)
- MUST NOT publish events without proper schema validation
- MUST NOT bypass DLQ (all failures must be logged)
- MUST NOT process same event twice without idempotency checks
- MUST NOT block API requests waiting for event processing

### SHOULD Consider:

**Recommended Practices**:
- Use separate Redis instances for events vs. caching
- Implement event versioning for schema evolution
- Add event size limits (max 1MB payload)
- Monitor consumer lag and scale workers accordingly
- Implement circuit breakers for external API calls
- Use distributed tracing (correlation_id across services)

## Rationale

### Why Redis over RabbitMQ/Kafka:

| Aspect | Redis | RabbitMQ | Kafka | Winner |
|--------|-------|----------|-------|--------|
| **Setup Complexity** | Low | Medium | High | Redis ✓ |
| **Operations** | Simple | Complex | Very Complex | Redis ✓ |
| **Team Expertise** | High | Low | None | Redis ✓ |
| **Performance** | 100K+ msg/s | 50K msg/s | 1M+ msg/s | Redis ✓ (sufficient) |
| **Persistence** | AOF (append-only) | Disk | Disk + replication | Kafka better |
| **Ordering** | Yes (streams) | Yes | Yes | Tie |
| **Ecosystem** | Large | Large | Large | Tie |

**Decision**: Redis Streams for now, migrate to Kafka if we hit scale limits (>1M events/day).

### Why Event-Driven:

1. **Decoupling**: API servers don't need to know about workers
2. **Scalability**: Scale workers independently from API servers
3. **Reliability**: Retries and DLQ prevent data loss
4. **Performance**: API responds in <200ms instead of 5+ seconds
5. **Flexibility**: Easy to add new event handlers without changing API

## Compliance

**Stories must be rejected if they**:
- Perform long-running operations (>3s) synchronously in API endpoints
- Block API responses waiting for email/notification delivery
- Generate reports synchronously without event-driven approach
- Skip event publishing for async operations
- Bypass DLQ for failed events

**Stories should be flagged for review if they**:
- Add new event types (need to document handlers)
- Change event schema (versioning required)
- Introduce external API calls (might need async)
- Process large datasets (might need async)
- Send notifications (should use events)

## Migration Path

**Current** (synchronous):
```python
@app.post("/users")
def create_user(user: UserCreate):
    user = db.create_user(user)
    send_email(user.email, "welcome")  # Blocks for 3 seconds
    return {"id": user.id}
```

**Target** (event-driven):
```python
@app.post("/users")
def create_user(user: UserCreate):
    user = db.create_user(user)
    publish_event("user.registered", {"user_id": user.id, "email": user.email})
    return {"id": user.id}  # Returns immediately
```

## Review Date

**Next Review**: 2024-08-10 (6 months) or when reaching 1M events/day.

## References

- Redis Streams Documentation: https://redis.io/docs/data-types/streams/
- Martin Fowler: Event-Driven Architecture
- AWS Event-Driven Architecture Best Practices
- Internal: Async Task Processing Benchmarks (2024-Q1)

---

**Last Updated**: 2024-02-10
**Version**: 1.0
**Owner**: Architecture Team
