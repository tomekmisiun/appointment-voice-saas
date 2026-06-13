# Alertmanager local stub

The bundled `alertmanager.yml` is a **local development stub**. It routes alerts
to the in-memory `local-dev` receiver, which does not send email, Slack, PagerDuty,
or any other external notification.

Use this file to verify that Prometheus alert rules fire end-to-end in the local
observability stack. For staging or production, replace the receiver with your
on-call integration and keep secrets out of git.

Example production receiver sketch (not applied by default):

```yaml
receivers:
  - name: oncall
    webhook_configs:
      - url: https://example.invalid/oncall/webhook
        send_resolved: true
```

See `docs/observability-production.md` for deployment guidance.
