"""
main.py — Entry point. Run this once a day (via cron / Task Scheduler).

    python main.py

Steps each run:
  1. Authenticate Gmail (cached after first run — no repeated logins)
  2. Fetch jobs from all enabled free sources
  3. Filter by your keywords/excludes/location
  4. Log new (deduped) jobs to local SQLite
  5. Email you a digest with drafted cover letters
  6. Check for applications needing a 7-day follow-up reminder
"""
import yaml
import db
import sources
import filters
import digest
import gmail_client


def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)


def main():
    config = load_config()
    db.init_db()

    print("[main] Authenticating with Gmail...")
    gmail_service = gmail_client.get_gmail_service()

    print("[main] Fetching jobs from enabled sources...")
    raw_jobs = sources.fetch_all(config, gmail_service=gmail_service)
    print(f"[main] Fetched {len(raw_jobs)} raw listings.")

    matched = filters.filter_jobs(raw_jobs, config)
    print(f"[main] {len(matched)} listings matched your keywords.")

    new_count = 0
    for job in matched:
        inserted = db.add_job(
            title=job["title"],
            company=job["company"],
            location=job.get("location", ""),
            url=job["url"],
            source=job["source"],
        )
        if inserted:
            new_count += 1
    print(f"[main] {new_count} new jobs logged (rest were duplicates already tracked).")

    digest.send_daily_digest(config, gmail_service)
    digest.send_follow_up_reminders(config, gmail_service)

    print("[main] Done.")


if __name__ == "__main__":
    main()
