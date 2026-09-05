"""
app.py — Web entry point for deploying on Render's FREE Web Service tier.

Endpoints:
  GET /                          -> health check (JSON)
  GET /run?token=...             -> triggers a job-tracker run (used by cron-job.org)
  GET /dashboard?token=...       -> browser-friendly page: view jobs, mark
                                     Applied/Ignored, from your phone or laptop
                                     anywhere — this is your "frontend".
"""
import os
import threading
from flask import Flask, request, jsonify, Response

import db
import main as job_main

app = Flask(__name__)

# Same secret you set in Render's Environment Variables.
RUN_SECRET = os.environ.get("RUN_SECRET", "")

_last_run_status = {"state": "never run"}


def _check_token():
    return RUN_SECRET and request.args.get("token") == RUN_SECRET


def _run_job_safely():
    global _last_run_status
    _last_run_status = {"state": "running"}
    try:
        job_main.main()
        _last_run_status = {"state": "ok"}
    except Exception as e:
        _last_run_status = {"state": "error", "detail": str(e)}
        print(f"[app] Job run failed: {e}")


@app.route("/")
def health():
    return jsonify({"status": "alive", "last_run": _last_run_status})


@app.route("/run")
def run_endpoint():
    if not RUN_SECRET:
        return jsonify({"error": "RUN_SECRET not configured on server"}), 500
    if not _check_token():
        return jsonify({"error": "unauthorized"}), 403

    thread = threading.Thread(target=_run_job_safely, daemon=True)
    thread.start()
    return jsonify({"status": "started"})


@app.route("/mark")
def mark_endpoint():
    """Called by buttons on the dashboard to change a job's status."""
    if not _check_token():
        return jsonify({"error": "unauthorized"}), 403

    job_id = request.args.get("id")
    action = request.args.get("action")
    if not job_id or action not in ("applied", "ignore"):
        return jsonify({"error": "bad request"}), 400

    if action == "applied":
        db.mark_status(job_id, "applied", extra_field="applied_at")
    else:
        db.mark_status(job_id, "ignored")

    return dashboard()  # redraw the dashboard with the updated status


@app.route("/dashboard")
def dashboard():
    if not _check_token():
        return Response("Unauthorized. Add ?token=YOUR_RUN_SECRET to the URL.", status=403)

    jobs = db.list_all(limit=100)
    token = request.args.get("token")

    rows_html = ""
    if not jobs:
        rows_html = "<p style='color:#888;'>No jobs tracked yet. Trigger a run from cron-job.org or wait for the next scheduled one.</p>"

    for j in jobs:
        status_color = {
            "new": "#999",
            "sent": "#0a84ff",
            "applied": "#22a559",
            "reminded": "#e0a500",
            "ignored": "#555",
        }.get(j["status"], "#999")

        buttons = ""
        if j["status"] not in ("applied", "ignored"):
            buttons = f"""
              <a href="/mark?id={j['id']}&action=applied&token={token}"
                 style="background:#22a559;color:white;padding:6px 12px;border-radius:6px;text-decoration:none;font-size:13px;margin-right:6px;">Mark Applied</a>
              <a href="/mark?id={j['id']}&action=ignore&token={token}"
                 style="background:#555;color:white;padding:6px 12px;border-radius:6px;text-decoration:none;font-size:13px;">Ignore</a>
            """

        applied_note = f"<div style='font-size:12px;color:#888;'>Applied: {j['applied_at'][:10]}</div>" if j["applied_at"] else ""

        rows_html += f"""
        <div style="border:1px solid #333;border-radius:10px;padding:14px;margin-bottom:12px;background:#111;">
          <div style="display:flex;justify-content:space-between;align-items:start;">
            <div>
              <div style="font-weight:600;font-size:16px;color:#fff;">{j['title']}</div>
              <div style="color:#aaa;font-size:13px;">{j['company']} &middot; {j['location']} &middot; {j['source']}</div>
            </div>
            <span style="background:{status_color};color:white;padding:2px 10px;border-radius:12px;font-size:12px;text-transform:uppercase;">{j['status']}</span>
          </div>
          {applied_note}
          <div style="margin-top:10px;">
            <a href="{j['url']}" target="_blank" style="color:#4da3ff;font-size:13px;">View listing &rarr;</a>
          </div>
          <div style="margin-top:10px;">{buttons}</div>
        </div>
        """

    html = f"""
    <html>
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Job Tracker Dashboard</title>
    </head>
    <body style="font-family:-apple-system,Arial,sans-serif;background:#000;color:#eee;max-width:700px;margin:0 auto;padding:16px;">
      <h2 style="margin-bottom:4px;">🧭 Job Tracker Dashboard</h2>
      <p style="color:#888;font-size:13px;margin-top:0;">
        {len(jobs)} tracked jobs. Trigger a fresh run any time:
        <a href="/run?token={token}" style="color:#4da3ff;">Run now</a>
      </p>
      {rows_html}
    </body>
    </html>
    """
    return Response(html, mimetype="text/html")


if __name__ == "__main__":
    db.init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
