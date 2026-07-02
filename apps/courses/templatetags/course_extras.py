from django import template

register = template.Library()


@register.filter
def duration(seconds):
    """Convert seconds to human-readable format: Xh Ym Zs"""
    if seconds is None:
        return "—"
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    parts = []
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    if s or not parts:
        parts.append(f"{s}s")
    return " ".join(parts)
