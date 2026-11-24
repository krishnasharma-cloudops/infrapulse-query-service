def status(age_seconds, values, threshold, stale_seconds):
    if age_seconds is None or age_seconds > stale_seconds:
        return 'offline'
    return 'warning' if any(v >= threshold for v in values) else 'online'
