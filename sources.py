"""
sources.py — Pulls job listings from FREE sources only.

Each function returns a list of dicts:
    {"title": ..., "company": ..., "location": ..., "url": ..., "source": ...}

Sources:
  1. RemoteOK          — free public JSON API, no key
  2. We Work Remotely   — free public RSS feed
  3. Hacker News "Who's Hiring" — free Algolia HN Search API
  4. Gmail Job Alerts   — reads LinkedIn/Indeed alert emails already in your inbox
     (avoids scraping LinkedIn directly, which their ToS prohibits)
"""
import requests
import feedparser
import re


def fetch_remoteok():
    jobs = []
    try:
        r = requests.get("https://remoteok.com/api", headers={"User-Agent": "job-tracker-agent"}, timeout=15)
        r.raise_for_status()
        data = r.json()
        for entry in data:
            if not isinstance(entry, dict) or "position" not in entry:
                continue
            jobs.append({
                "title": entry.get("position", ""),
                "company": entry.get("company", "Unknown"),
                "location": entry.get("location", "Remote"),
                "url": entry.get("url", ""),
                "source": "RemoteOK",
            })
    except Exception as e:
        print(f"[sources] RemoteOK fetch failed: {e}")
    return jobs


def fetch_weworkremotely():
    jobs = []
    feeds = [
        "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    ]
    for feed_url in feeds:
        try:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries:
                title = entry.get("title", "")
                # WWR titles are usually "Company: Job Title"
                company, _, job_title = title.partition(":")
                jobs.append({
                    "title": job_title.strip() or title,
                    "company": company.strip(),
                    "location": "Remote",
                    "url": entry.get("link", ""),
                    "source": "WeWorkRemotely",
                })
        except Exception as e:
            print(f"[sources] WeWorkRemotely fetch failed: {e}")
    return jobs


def fetch_hn_hiring():
    """Finds the latest 'Ask HN: Who is hiring?' thread and pulls top-level comments."""
    jobs = []
    try:
        search = requests.get(
            "https://hn.algolia.com/api/v1/search_by_date",
            params={"query": "Who is hiring", "tags": "story", "hitsPerPage": 5},
            timeout=15,
        ).json()
        thread_id = None
        for hit in search.get("hits", []):
            if hit.get("title", "").lower().startswith("ask hn: who is hiring"):
                thread_id = hit["objectID"]
                break
        if not thread_id:
            return jobs

        item = requests.get(f"https://hn.algolia.com/api/v1/items/{thread_id}", timeout=15).json()
        for comment in item.get("children", []):
            text = (comment.get("text") or "")
            clean_text = re.sub("<[^<]+?>", " ", text)  # strip HTML tags
            if not clean_text.strip():
                continue
            first_line = clean_text.strip().split("\n")[0][:200]
            jobs.append({
                "title": first_line,
                "company": "(see HN thread)",
                "location": "Varies",
                "url": f"https://news.ycombinator.com/item?id={comment.get('id')}",
                "source": "HN Who's Hiring",
            })
    except Exception as e:
        print(f"[sources] HN Hiring fetch failed: {e}")
    return jobs


def fetch_gmail_job_alerts(gmail_service, max_results=25):
    """
    Reads LinkedIn Job Alert / Indeed Job Alert emails from Gmail and extracts
    listings mentioned in them. Requires an authenticated Gmail API service
    (see gmail_client.py). This is the recommended way to get LinkedIn jobs,
    since LinkedIn has no free scraping-safe API.
    """
    jobs = []
    if gmail_service is None:
        return jobs

    query = 'from:(jobs-noreply@linkedin.com OR alert@indeed.com) newer_than:2d'
    try:
        results = gmail_service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()
        message_ids = [m["id"] for m in results.get("messages", [])]

        for mid in message_ids:
            msg = gmail_service.users().messages().get(
                userId="me", id=mid, format="full"
            ).execute()
            snippet = msg.get("snippet", "")
            subject = ""
            for header in msg.get("payload", {}).get("headers", []):
                if header["name"] == "Subject":
                    subject = header["value"]
            jobs.append({
                "title": subject or snippet[:100],
                "company": "(see email)",
                "location": "See email",
                "url": f"https://mail.google.com/mail/u/0/#inbox/{mid}",
                "source": "Gmail Job Alert",
            })
    except Exception as e:
        print(f"[sources] Gmail job alert fetch failed: {e}")
    return jobs


def fetch_all(config, gmail_service=None):
    all_jobs = []
    src_cfg = config.get("sources", {})

    if src_cfg.get("remoteok"):
        all_jobs += fetch_remoteok()
    if src_cfg.get("weworkremotely"):
        all_jobs += fetch_weworkremotely()
    if src_cfg.get("hn_hiring"):
        all_jobs += fetch_hn_hiring()
    if src_cfg.get("gmail_job_alerts"):
        all_jobs += fetch_gmail_job_alerts(gmail_service)

    return all_jobs
