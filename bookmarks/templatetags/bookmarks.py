from django import template

from bookmarks.forms import BookmarkSearchForm
from bookmarks.models import BookmarkSearch

register = template.Library()


@register.inclusion_tag(
    "bookmarks/search.html", name="bookmark_search", takes_context=True
)
def bookmark_search(context, search: BookmarkSearch, mode: str = ""):
    search_form = BookmarkSearchForm(search, editable_fields=["q"])

    if mode == "shared":
        preferences_form = BookmarkSearchForm(search, editable_fields=["sort"])
    else:
        preferences_form = BookmarkSearchForm(
            search,
            editable_fields=[
                "sort",
                "shared",
                "unread",
                "tagged",
                "date_filter_by",
                "date_filter_type",
                "date_filter_relative_string",
                "date_filter_start",
                "date_filter_end",
            ],
        )
    return {
        "request": context["request"],
        "app_version": context["app_version"],
        "search": search,
        "search_form": search_form,
        "preferences_form": preferences_form,
        "mode": mode,
    }
