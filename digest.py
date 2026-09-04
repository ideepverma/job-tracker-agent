"""
digest.py — Composes and sends:
  1. Daily digest of new matching jobs (with cover letter draft link per job)
  2. Follow-up reminder emails for jobs applied >= N days ago
"""
import db
import cover_letter
import gmail_client


def build_digest_html(jobs_with_letters):
    if not jobs_with_letters:
        return None

    rows = []
    for job, letter in jobs_with_letters:
        rows.append(f"""
        <div style="border:1px solid #ddd;border-radius:8px;padding:16px;margin-bottom:14px;">
          <h3 style="margin:0 0 4px 0;">{job['title']}</h3>
          <p style="margin:0 0 8px 0;color:#555;">
            {job['company']} &middot; {job['location']} &middot; source: {job['source']}
          </p>
          <p><a href="{job['url']}">View listing &rarr;</a></p>
          <details>
            <summary style="cursor:pointer;color:#0a5;">Draft cover letter</summary>
            <pre style="white-space:pre-wrap;font-family:inherit;background:#f7f7f7;padding:10px;border-radius:6px;">{letter}</pre>
          </details>
          <p style="font-size:12px;color:#888;">Job ID: {job['id']} — mark applied with:
            <code>python cli.py applied {job['id']}</code>
          </p>
        </div>
        """)

    return f"""
    <html><body style="font-family:Arial,sans-serif;max-width:700px;margin:auto;">
      <h2>Your Job Tracker Digest — {len(jobs_with_letters)} new matches</h2>
      {''.join(rows)}
    </body></html>
    """


def send_daily_digest(config, gmail_service):
    new_jobs = db.get_new_jobs()
    if not new_jobs:
        print("[digest] No new jobs to send.")
        return

    candidate = config.get("candidate", {})
    use_ollama = config.get("use_ollama", False)

    jobs_with_letters = []
    for job in new_jobs:
        letter = cover_letter.generate(dict(job), candidate, use_ollama=use_ollama)
        jobs_with_letters.append((job, letter))

    html = build_digest_html(jobs_with_letters)
    if html is None:
        return

    gmail_client.send_email(
        gmail_service,
        to=config["user_email"],
        subject=f"🧭 {len(new_jobs)} new job matches",
        body_html=html,
    )
    db.mark_sent_batch([j["id"] for j in new_jobs])
    print(f"[digest] Sent digest with {len(new_jobs)} jobs.")


def send_follow_up_reminders(config, gmail_service):
    days = config.get("follow_up_days", 7)
    due = db.get_applied_jobs_needing_reminder(days)
    if not due:
        print("[digest] No follow-up reminders due.")
        return

    rows = "".join(
        f"<li><b>{j['title']}</b> at {j['company']} — applied {j['applied_at'][:10]}. "
        f'<a href="{j["url"]}">View</a></li>'
        for j in due
    )
    html = f"""
    <html><body style="font-family:Arial,sans-serif;">
      <h2>⏰ Time to follow up ({days}+ days since you applied)</h2>
      <ul>{rows}</ul>
      <p>Consider sending a short follow-up note to the recruiter or hiring manager.</p>
    </body></html>
    """
    gmail_client.send_email(
        gmail_service,
        to=config["user_email"],
        subject=f"⏰ Follow-up reminder: {len(due)} application(s)",
        body_html=html,
    )
    for j in due:
        db.mark_status(j["id"], "reminded", extra_field="reminded_at")
    print(f"[digest] Sent {len(due)} follow-up reminder(s).")
