# Webhook And Idempotency

This template provides provider-neutral webhook verification and request
idempotency primitives for external integrations.

## Inbound Webhook Verification

`POST /api/v1/webhooks/inbound` requires:

- `Idempotency-Key`: client-generated replay-safe request key
- `X-Webhook-Timestamp`: Unix timestamp in seconds
- `X-Webhook-Signature`: HMAC-SHA256 hex digest of `{timestamp}.{raw_body}`

The server rejects requests when:

- the signature secret is missing or invalid
- the timestamp is outside the configured replay window
- the `(provider, event_id)` pair was already processed
- a duplicate in-flight request uses the same idempotency key

Configure:

- `WEBHOOK_SIGNATURE_SECRET`
- `WEBHOOK_SIGNATURE_TOLERANCE_SECONDS` (default: `300`)
- `IDEMPOTENCY_TTL_SECONDS` (default: `86400`)
- `IDEMPOTENCY_PROCESSING_LOCK_TTL_SECONDS` (default: `60`)

Production validation requires a non-placeholder webhook secret with at least
32 characters.

## Provider Patterns

### Generic Timestamped HMAC

Send separate headers:

```http
X-Webhook-Timestamp: 1718123456
X-Webhook-Signature: <hmac-sha256-hex of "1718123456." + raw_body>
Idempotency-Key: req_123
```

### Stripe-Compatible Combined Signature

You may also send a combined signature header without
`X-Webhook-Timestamp`:

```http
X-Webhook-Signature: t=1718123456,v1=<hmac-sha256-hex>
```

The verifier extracts the timestamp from `t=` and validates the replay window
before checking `v1`.

### GitHub-Style Guidance

GitHub uses `X-Hub-Signature-256` with a different prefix format. For GitHub
webhooks, map the provider timestamp and signature into this template's
headers at your ingress layer, or add a provider-specific adapter route that
translates GitHub headers into the generic verification contract documented
here.

## Idempotency Guarantees

Idempotency records are stored in PostgreSQL keyed by a hashed scope plus
client key. Successful responses are cached until `IDEMPOTENCY_TTL_SECONDS`
expires.

Concurrent duplicate requests with the same idempotency key use a Redis
processing lock:

1. return a cached response when one already exists
2. acquire a short-lived Redis lock before processing
3. return `409 Duplicate request is already in progress` when another request
   holds the lock
4. store the final response and release the lock

If two requests race to persist the same idempotency record, the unique
constraint fallback returns the first stored response.

## Recommended Production Checklist

- rotate webhook secrets independently from `SECRET_KEY`
- keep replay windows short (5 minutes or less unless a provider requires more)
- treat `409 duplicate` webhook events as safe no-ops
- monitor repeated `Duplicate request is already in progress` responses as a
  sign of client retry storms or slow handlers
