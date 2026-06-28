# Twilio Provider Runbook (AVS-H007)

Operator reference for configuring and operating the Twilio voice and SMS
integrations. Complete before routing real calls or messages.

## 1. Required credentials

| Setting | Description |
|---|---|
| `TWILIO_ACCOUNT_SID` | Twilio Account SID (starts with `AC`) |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token (from console) |
| `TWILIO_VOICE_NUMBER` | E.164 inbound Voice number seeded into the public demo business, currently `+18174057514` |
| `TWILIO_SMS_FROM` | SMS sender used by the provider. May be an E.164 number or an approved alphanumeric Sender ID such as `VoxSlot` |
| `TWILIO_VOICE_BASE_URL` | Public HTTPS base URL of your API, e.g. `https://api.example.com` |

Store all values in environment variables or a secrets manager. Never commit
them to source control.

Voice, owner notifications, and SMS sender are separate values:

- Voice number: customers call `+18174057514`; Twilio sends this as the
  webhook `To=` value and the backend matches it to `businesses.phone`.
- Owner notification number: the demo business stores `+48505460409` in
  `businesses.owner_notification_phone`; this is the SMS recipient for owner
  alerts.
- SMS sender: outbound SMS uses `TWILIO_SMS_FROM`, currently `VoxSlot`. Do not
  reuse the Voice number as the SMS sender unless the Twilio account is
  intentionally configured that way.

## 2. Twilio console setup

### Voice webhook

1. Purchase a phone number in the Twilio console.
2. Set the "A call comes in" webhook to:
   ```
   POST https://<your-domain>/api/v1/webhooks/twilio/voice
   ```
   No path parameters are needed. The backend identifies the business from the
   `To=` field Twilio sends in the request body, matched against the
   `businesses.phone` column for the provisioned number.
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
| IVR returns "not configured" | No business with matching `phone` for the `To=` number | Verify the provisioned Twilio number matches `businesses.phone` |
| SMS not delivered | `NullSmsProvider` active | Check `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_SMS_FROM` are set |
| SMS rejected with invalid sender | Twilio account/route does not accept the alphanumeric Sender ID | Keep `TWILIO_SMS_FROM=VoxSlot`; enable or verify alphanumeric Sender ID support in Twilio instead of silently falling back |
| SMS status stays `SENT` | Status callback URL not configured | Set status callback URL in Twilio console |
| High failed-job queue depth | Twilio API returning errors | Check Twilio account balance and number status |

## 8. Rollback

To disable Twilio integrations without redeploying:

- Clear `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_SMS_FROM` →
  `get_sms_provider()` falls back to `NullSmsProvider` (SMS silently discarded).
- Remove or change the webhook URL in the Twilio console → voice calls stop
  routing to the IVR.
- The local IVR simulation endpoints (`/api/v1/ivr/simulate/*`) remain
  available for internal testing.
