"""
filters.py — Keeps only jobs matching your target roles and drops
anything matching your exclude list or location filters.
"""


def matches(job, config):
    text = f"{job.get('title', '')} {job.get('company', '')}".lower()

    keywords = [k.lower() for k in config.get("keywords", [])]
    excludes = [k.lower() for k in config.get("exclude_keywords", [])]
    locations = [l.lower() for l in config.get("location_filters", [])]

    if not any(kw in text for kw in keywords):
        return False

    if any(ex in text for ex in excludes):
        return False

    if locations:
        loc_text = job.get("location", "").lower()
        if not any(loc in loc_text or loc in text for loc in locations):
            return False

    return True


def filter_jobs(jobs, config):
    return [j for j in jobs if matches(j, config)]
