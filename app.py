"""
app.py — Web entry point for deploying on Render's FREE Web Service tier.
"""
import os
import threading
from flask import Flask, request, jsonify

import db
import main as job_main

app = Flask(__name__)

RUN_SECRET = os.environ.get("RUN_SECRET", "")

_last_run_status = {"state": "never run"}


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
    if request.args.get("token") != RUN_SECRET:
        return jsonify({"error": "unauthorized"}), 403

    thread = threading.Thread(target=_run_job_safely, daemon=True)
    thread.start()
    return jsonify({"status": "started"})


if __name__ == "__main__":
    db.init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
