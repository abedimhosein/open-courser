import markdown
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name="markdown")
def render_markdown(content):
    """Render Markdown content to HTML."""
    if not content:
        return ""
    html = markdown.markdown(
        content,
        extensions=["fenced_code", "tables", "nl2br", "sane_lists"],
    )
    return mark_safe(html)
