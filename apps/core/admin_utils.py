from django.template.loader import render_to_string
from django.utils.safestring import mark_safe


def user_chip(user) -> str:
    """Avatar + name, safe to return from a ModelAdmin list_display method
    wherever a row needs to show who a user is (not just their email)."""
    return mark_safe(render_to_string("unfold/helpers/user_chip.html", {"user": user}))
