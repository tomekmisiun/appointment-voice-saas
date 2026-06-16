# Twilio Provider Runbook (AVS-H007)

Operator reference for configuring and operating the Twilio voice and SMS
integrations. Complete before routing real calls or messages.

## 1. Required credentials

| Setting | Description |
|---|---|
| `TWILIO_ACCOUNT_SID` | Twilio Account SID (starts with `AC`) |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token (from console) |
| `TWILIO_FROM_NUMBER` | E.164 number purchased in Twilio, e.g. `+48800000001` |
| `TWILIO_VOICE_BASE_URL` | Public HTTPS base URL of your API, e.g. `https://api.example.com` |

Store all values in environment variables or a secrets manager. Never commit
them to source control.

## 2. Twilio console setup

### Voice webhook

1. Purchase a phone number in the Twilio console.
2. Set the "A call comes in" webhook to:
   ```
   POST https://<your-domain>/api/v1/webhooks/twilio/voice/<business_id>
   ```
   Replace `<business_id>` with the integer ID of the pilot business (from the
   database or admin API).
3. Leave the HTTP method as **POST**.
4. Twilio will follow gather action URLs automatically; no additional webhook
   configuration is needed for keypresses.

### SMS status callback

1. In the Twilio console → Messaging → Services (or per-number settings):
   set the **Status Callback URL** to:
   ```
   POST https://<your-domain>/api/v1/webhooks/twilio/sms/status
   ```
2. Twilio sends `SmsSid` + `MessageStatus` on delivery events. Failed or
   undelivered messages are marked as `FAILED` in the notification outbox.

## 3. Signature validation

Both webhook endpoints verify `X-Twilio-Signature` using HMAC-SHA1 and your
`TWILIO_AUTH_TOKEN`. Validation is **skipped when `TWILIO_AUTH_TOKEN` is
empty** — do not deploy to production without this set.

The signature is computed over the full request URL (including `https://` and
the path) plus sorted POST form parameters. Ensure your reverse proxy passes
the original `Host` header and does not rewrite the URL path.

## 4. Rate limits

| Endpoint | Default limit | Config keys |
|---|---|---|
| Voice webhooks (per IP) | 120 req / 60 s | `TWILIO_VOICE_RATE_LIMIT_LIMIT`, `TWILIO_VOICE_RATE_LIMIT_WINDOW_SECONDS` |
| SMS status webhooks (per IP) | 300 req / 60 s | `TWILIO_SMS_STATUS_RATE_LIMIT_LIMIT`, `TWILIO_SMS_STATUS_RATE_LIMIT_WINDOW_SECONDS` |

Twilio's IP ranges are documented at
<https://help.twilio.com/articles/5925535571483>. Consider allowlisting those
ranges at the WAF or load balancer to reduce abuse surface.

## 5. IVR session TTL

Twilio voice sessions expire after `IVR_SESSION_TTL_MINUTES` (default: 10).
If a caller waits longer between keypresses, the session returns an expiry
prompt and the call ends. Adjust the TTL to match your expected call duration.

## 6. Test call procedure

1. Confirm environment variables are set and the service is running.
2. Call the Twilio number from a real phone (or use the Twilio Test Console).
3. Verify the IVR welcome prompt plays.
4. Press `1`, select a service, select a slot.
5. Confirm a booking appears in the database:
   ```sql
   SELECT id, status, source, starts_at FROM bookings ORDER BY id DESC LIMIT 1;
   ```
6. Confirm an SMS notification is enqueued:
   ```sql
   SELECT id, status, recipient_phone FROM notification_outbox ORDER BY id DESC LIMIT 2;
   ```
7. Start the worker (`python -m app.worker`) and verify the SMS is sent and
   `provider_message_id` is populated.
8. Cancel the test booking via the API and confirm the cancellation SMS is
   enqueued.

## 7. Incident response

| Symptom | Likely cause | Action |
|---|---|---|
| 403 on voice webhook | Signature mismatch | Check `TWILIO_AUTH_TOKEN`; check reverse proxy URL rewriting |
| 422 on voice webhook | Missing `CallSid` or `From` form field | Check Twilio webhook method is POST |
| IVR returns "not configured" | Unknown `business_id` in URL | Verify webhook URL in Twilio console |
| SMS not delivered | `NullSmsProvider` active | Check `TWILIO_ACCOUNT_SID` / `TWILIO_FROM_NUMBER` are set |
| SMS status stays `SENT` | Status callback URL not configured | Set status callback URL in Twilio console |
| High failed-job queue depth | Twilio API returning errors | Check Twilio account balance and number status |

## 8. Rollback

To disable Twilio integrations without redeploying:

- Clear `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_FROM_NUMBER` →
  `get_sms_provider()` falls back to `NullSmsProvider` (SMS silently discarded).
- Remove or change the webhook URL in the Twilio console → voice calls stop
  routing to the IVR.
- The local IVR simulation endpoints (`/api/v1/ivr/simulate/*`) remain
  available for internal testing.
