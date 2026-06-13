from app.core.metrics import observe_worker_job, observe_worker_maintenance, render_metrics


def test_worker_metrics_are_rendered():
    observe_worker_job(job_type="demo", status="failed")
    observe_worker_maintenance(status="completed")

    metrics_output = render_metrics()

    assert 'worker_jobs_total{job_type="demo",status="failed"}' in metrics_output
    assert 'worker_maintenance_runs_total{status="completed"}' in metrics_output
