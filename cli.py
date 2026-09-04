"""
cli.py — Quick command-line control over your tracked jobs.

Usage:
    python cli.py list                # show recent tracked jobs
    python cli.py applied <job_id>     # mark a job as applied (starts 7-day timer)
    python cli.py ignore <job_id>      # stop tracking a job
    python cli.py search "backend"     # search tracked jobs by title/company
"""
import sys
import db


def print_job(j):
    print(f"[{j['id']}] {j['status']:9s} | {j['title']} — {j['company']} ({j['source']})")


def main():
    db.init_db()
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "list":
        for j in db.list_all():
            print_job(j)

    elif cmd == "applied" and len(sys.argv) == 3:
        db.mark_status(sys.argv[2], "applied", extra_field="applied_at")
        print(f"Marked {sys.argv[2]} as applied. Reminder will fire after follow_up_days.")

    elif cmd == "ignore" and len(sys.argv) == 3:
        db.mark_status(sys.argv[2], "ignored")
        print(f"Marked {sys.argv[2]} as ignored.")

    elif cmd == "search" and len(sys.argv) == 3:
        for j in db.search_jobs(sys.argv[2]):
            print_job(j)

    else:
        print(__doc__)


if __name__ == "__main__":
    main()
