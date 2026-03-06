from django import forms
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from bookmarks.models import (
    Bookmark,
    BookmarkBundle,
    BookmarkSearch,
    GlobalSettings,
    Tag,
    UserProfile,
    build_tag_string,
    parse_tag_string,
    sanitize_tag_name,
)
from bookmarks.services.bookmarks import create_bookmark, update_bookmark
from bookmarks.type_defs import HttpRequest
from bookmarks.validators import BookmarkURLValidator
from bookmarks.widgets import (
    FormCheckbox,
    FormErrorList,
    FormInput,
    FormNumberInput,
    FormSelect,
    FormTextarea,
    TagAutocomplete,
)


class BookmarkForm(forms.ModelForm):
    # Use URLField for URL
    url = forms.CharField(validators=[BookmarkURLValidator()], widget=FormInput)
    tag_string = forms.CharField(required=False, widget=TagAutocomplete)
    # Do not require title and description as they may be empty
    title = forms.CharField(max_length=512, required=False, widget=FormInput)
    description = forms.CharField(required=False, widget=FormTextarea)
    notes = forms.CharField(required=False, widget=FormTextarea)
    unread = forms.BooleanField(required=False, widget=FormCheckbox)
    shared = forms.BooleanField(required=False, widget=FormCheckbox)
    # Hidden field that determines whether to close window/tab after saving the bookmark
    auto_close = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Bookmark
        fields = [
            "url",
            "tag_string",
            "title",
            "description",
            "notes",
            "unread",
            "shared",
            "auto_close",
        ]

    def __init__(self, request: HttpRequest, instance: Bookmark = None):
        self.request = request

        initial = None
        if instance is None and request.method == "GET":
            initial = {
                "url": request.GET.get("url"),
                "title": request.GET.get("title"),
                "description": request.GET.get("description"),
                "notes": request.GET.get("notes"),
                "tag_string": request.GET.get("tags"),
                "auto_close": "auto_close" in request.GET,
                "unread": request.user_profile.default_mark_unread,
                "shared": request.user_profile.default_mark_shared,
            }
        if instance is not None and request.method == "GET":
            initial = {"tag_string": build_tag_string(instance.tag_names, " ")}
        data = request.POST if request.method == "POST" else None
        super().__init__(
            data, instance=instance, initial=initial, error_class=FormErrorList
        )

    @property
    def is_auto_close(self):
        return self.data.get("auto_close", False) == "True" or self.initial.get(
            "auto_close", False
        )

    @property
    def has_notes(self):
        return self.initial.get("notes", None) or (
            self.instance and self.instance.notes
        )

    def save(self, commit=False):
        tag_string = convert_tag_string(self.data["tag_string"])
        bookmark = super().save(commit=False)
        if self.instance.pk:
            return update_bookmark(bookmark, tag_string, self.request.user)
        else:
            return create_bookmark(bookmark, tag_string, self.request.user)

    def clean_url(self):
        # When creating a bookmark, the service logic prevents duplicate URLs by
        # updating the existing bookmark instead, which is also communicated in
        # the form's UI. When editing a bookmark, there is no assumption that
        # it would update a different bookmark if the URL is a duplicate, so
        # raise a validation error in that case.
        url = self.cleaned_data["url"]
        if self.instance.pk:
            is_duplicate = (
                Bookmark.query_existing(self.instance.owner, url)
                .exclude(pk=self.instance.pk)
                .exists()
            )
            if is_duplicate:
                raise forms.ValidationError("A bookmark with this URL already exists.")

        return url


def convert_tag_string(tag_string: str):
    # Tag strings coming from inputs are space-separated, however services.bookmarks functions expect comma-separated
    # strings
    return tag_string.replace(" ", ",")


class TagForm(forms.ModelForm):
    name = forms.CharField(widget=FormInput)

    class Meta:
        model = Tag
        fields = ["name"]

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs, error_class=FormErrorList)
        self.user = user

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()

        name = sanitize_tag_name(name)

        queryset = Tag.objects.filter(name__iexact=name, owner=self.user)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise forms.ValidationError(f'Tag "{name}" already exists.')

        return name

    def save(self, commit=True):
        tag = super().save(commit=False)
        if not self.instance.pk:
            tag.owner = self.user
            tag.date_added = timezone.now()
        else:
            tag.date_modified = timezone.now()
        if commit:
            tag.save()
        return tag


class TagMergeForm(forms.Form):
    target_tag = forms.CharField(widget=TagAutocomplete)
    merge_tags = forms.CharField(widget=TagAutocomplete)

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs, error_class=FormErrorList)
        self.user = user

    def clean_target_tag(self):
        target_tag_name = self.cleaned_data.get("target_tag", "")

        target_tag_names = parse_tag_string(target_tag_name, " ")
        if len(target_tag_names) != 1:
            raise forms.ValidationError(
                "Please enter only one tag name for the target tag."
            )

        target_tag_name = target_tag_names[0]

        try:
            target_tag = Tag.objects.get(name__iexact=target_tag_name, owner=self.user)
        except Tag.DoesNotExist:
            raise forms.ValidationError(
                f'Tag "{target_tag_name}" does not exist.'
            ) from None

        return target_tag

    def clean_merge_tags(self):
        merge_tags_string = self.cleaned_data.get("merge_tags", "")

        merge_tag_names = parse_tag_string(merge_tags_string, " ")
        if not merge_tag_names:
            raise forms.ValidationError("Please enter at least one tag to merge.")

        merge_tags = []
        for tag_name in merge_tag_names:
            try:
                tag = Tag.objects.get(name__iexact=tag_name, owner=self.user)
                merge_tags.append(tag)
            except Tag.DoesNotExist:
                raise forms.ValidationError(
                    f'Tag "{tag_name}" does not exist.'
                ) from None

        target_tag = self.cleaned_data.get("target_tag")
        if target_tag and target_tag in merge_tags:
            raise forms.ValidationError(
                "The target tag cannot be selected for merging."
            )

        return merge_tags


class BookmarkBundleForm(forms.ModelForm):
    FILTER_TAGGED_CHOICES = [
        ("off", _("All")),
        ("yes", _("Has tags")),
        ("no", _("No tags")),
    ]
    BUNDLE_DATE_BY_CHOICES = [
        ("", _("All")),
        (BookmarkSearch.FILTER_DATE_BY_ADDED, _("Added")),
        (BookmarkSearch.FILTER_DATE_BY_MODIFIED, _("Modified")),
    ]
    BUNDLE_DATE_RELATIVE_CHOICES = [
        ("", "--"),
        ("today", _("Today")),
        ("yesterday", _("Yesterday")),
        ("this_week", _("This week")),
        ("this_month", _("This month")),
        ("this_year", _("This year")),
        ("last_7_days", _("Last 7 days")),
        ("last_30_days", _("Last 30 days")),
    ]

    name = forms.CharField(max_length=256, widget=FormInput)
    search = forms.CharField(max_length=256, required=False, widget=FormInput)
    filter_tagged = forms.ChoiceField(
        choices=FILTER_TAGGED_CHOICES,
        required=False,
        widget=FormSelect,
    )
    any_tags = forms.CharField(required=False, widget=TagAutocomplete)
    bundle_date_filter_by = forms.ChoiceField(
        choices=BUNDLE_DATE_BY_CHOICES,
        required=False,
        widget=FormSelect,
    )
    bundle_date_filter_relative_string = forms.ChoiceField(
        required=False,
        choices=BUNDLE_DATE_RELATIVE_CHOICES,
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    BUNDLE_FILTER_UNREAD_CHOICES = [
        (BookmarkBundle.FILTER_STATE_OFF, _("All")),
        (BookmarkBundle.FILTER_STATE_YES, _("Unread")),
        (BookmarkBundle.FILTER_STATE_NO, _("Read")),
    ]
    BUNDLE_FILTER_SHARED_CHOICES = [
        (BookmarkBundle.FILTER_STATE_OFF, _("All")),
        (BookmarkBundle.FILTER_STATE_YES, _("Shared")),
        (BookmarkBundle.FILTER_STATE_NO, _("Unshared")),
    ]
    filter_unread = forms.ChoiceField(
        choices=BUNDLE_FILTER_UNREAD_CHOICES,
        required=False,
        widget=FormSelect,
    )
    filter_shared = forms.ChoiceField(
        choices=BUNDLE_FILTER_SHARED_CHOICES,
        required=False,
        widget=FormSelect,
    )

    class Meta:
        model = BookmarkBundle
        fields = [
            "name",
            "search",
            "filter_unread",
            "filter_shared",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, error_class=FormErrorList)
        if self.instance and self.instance.pk:
            params = self.instance.search_params or {}
            if params.get("tagged") == BookmarkSearch.FILTER_TAGGED_UNTAGGED:
                self.fields["filter_tagged"].initial = "no"
                self.fields["any_tags"].initial = ""
            else:
                tags_value = self.instance.any_tags or self.instance.all_tags
                self.fields["filter_tagged"].initial = "yes" if tags_value else "off"
                self.fields["any_tags"].initial = tags_value or ""
            self.fields["bundle_date_filter_by"].initial = params.get(
                "date_filter_by", ""
            )
            self.fields["bundle_date_filter_relative_string"].initial = params.get(
                "date_filter_relative_string", ""
            )
        else:
            self.fields["filter_tagged"].initial = self.initial.get(
                "filter_tagged", "off"
            )
            self.fields["any_tags"].initial = self.initial.get("any_tags", "")
            self.fields["bundle_date_filter_by"].initial = self.initial.get(
                "bundle_date_filter_by", ""
            )
            self.fields["bundle_date_filter_relative_string"].initial = self.initial.get(
                "bundle_date_filter_relative_string", ""
            )

    def save(self, commit=True):
        instance = super().save(commit=False)
        filter_tagged = self.cleaned_data.get("filter_tagged")
        if filter_tagged == "yes" and self.cleaned_data.get("any_tags"):
            instance.any_tags = self.cleaned_data["any_tags"]
        else:
            instance.any_tags = ""
        instance.all_tags = ""
        instance.excluded_tags = ""
        params = dict(instance.search_params) if instance.search_params else {}
        if filter_tagged == "no":
            params["tagged"] = BookmarkSearch.FILTER_TAGGED_UNTAGGED
        else:
            params.pop("tagged", None)
        if self.cleaned_data.get("bundle_date_filter_by") and self.cleaned_data.get(
            "bundle_date_filter_relative_string"
        ):
            params["date_filter_by"] = self.cleaned_data["bundle_date_filter_by"]
            params["date_filter_type"] = BookmarkSearch.FILTER_DATE_TYPE_RELATIVE
            params["date_filter_relative_string"] = self.cleaned_data[
                "bundle_date_filter_relative_string"
            ]
        else:
            params.pop("date_filter_by", None)
            params.pop("date_filter_type", None)
            params.pop("date_filter_relative_string", None)
        instance.search_params = params
        if commit:
            instance.save()
        return instance

class BookmarkSearchForm(forms.Form):
    SORT_CHOICES = [
        (BookmarkSearch.SORT_ADDED_ASC, _("Added ↑")),
        (BookmarkSearch.SORT_ADDED_DESC, _("Added ↓")),
        (BookmarkSearch.SORT_TITLE_ASC, _("Title ↑")),
        (BookmarkSearch.SORT_TITLE_DESC, _("Title ↓")),
        (BookmarkSearch.SORT_RANDOM, _("Random")),
    ]
    FILTER_SHARED_CHOICES = [
        (BookmarkSearch.FILTER_SHARED_OFF, _("Off")),
        (BookmarkSearch.FILTER_SHARED_SHARED, _("Shared")),
        (BookmarkSearch.FILTER_SHARED_UNSHARED, _("Unshared")),
    ]
    FILTER_UNREAD_CHOICES = [
        (BookmarkSearch.FILTER_UNREAD_OFF, _("Off")),
        (BookmarkSearch.FILTER_UNREAD_YES, _("Unread")),
        (BookmarkSearch.FILTER_UNREAD_NO, _("Read")),
    ]
    FILTER_TAGGED_CHOICES = [
        (BookmarkSearch.FILTER_TAGGED_OFF, _("Off")),
        (BookmarkSearch.FILTER_TAGGED_TAGGED, _("Tagged")),
        (BookmarkSearch.FILTER_TAGGED_UNTAGGED, _("Untagged")),
    ]
    FILTER_DATE_BY_CHOICES = [
        (BookmarkSearch.FILTER_DATE_OFF, _("Off")),
        (BookmarkSearch.FILTER_DATE_BY_ADDED, _("Added")),
        (BookmarkSearch.FILTER_DATE_BY_MODIFIED, _("Modified")),
    ]
    FILTER_DATE_TYPE_CHOICES = [
        (BookmarkSearch.FILTER_DATE_TYPE_ABSOLUTE, _("Absolute")),
        (BookmarkSearch.FILTER_DATE_TYPE_RELATIVE, _("Relative")),
    ]

    q = forms.CharField()
    user = forms.ChoiceField(required=False, widget=FormSelect)
    bundle = forms.CharField(required=False)
    sort = forms.ChoiceField(choices=SORT_CHOICES, widget=FormSelect)
    shared = forms.ChoiceField(choices=FILTER_SHARED_CHOICES, widget=forms.RadioSelect)
    unread = forms.ChoiceField(choices=FILTER_UNREAD_CHOICES, widget=forms.RadioSelect)
    tagged = forms.ChoiceField(choices=FILTER_TAGGED_CHOICES, widget=forms.RadioSelect)
    modified_since = forms.CharField(required=False)
    added_since = forms.CharField(required=False)
    date_filter_by = forms.ChoiceField(
        choices=FILTER_DATE_BY_CHOICES, widget=forms.RadioSelect
    )
    date_filter_type = forms.ChoiceField(
        choices=FILTER_DATE_TYPE_CHOICES, widget=forms.RadioSelect
    )
    DATE_RELATIVE_CHOICES = [
        ("", "--"),
        ("today", _("Today")),
        ("yesterday", _("Yesterday")),
        ("this_week", _("This week")),
        ("this_month", _("This month")),
        ("this_year", _("This year")),
        ("last_7_days", _("Last 7 days")),
        ("last_30_days", _("Last 30 days")),
    ]
    date_filter_relative_string = forms.ChoiceField(
        required=False,
        choices=DATE_RELATIVE_CHOICES,
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    date_filter_start = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    date_filter_end = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"})
    )

    def __init__(
        self,
        search: BookmarkSearch,
        editable_fields: list[str] = None,
        users: list[User] = None,
    ):
        super().__init__()
        editable_fields = editable_fields or []
        self.editable_fields = editable_fields

        # set choices for user field if users are provided
        if users:
            user_choices = [(user.username, user.username) for user in users]
            user_choices.insert(0, ("", "Everyone"))
            self.fields["user"].choices = user_choices

        for param in search.params:
            if param in ("date_filter_start", "date_filter_end"):
                value = getattr(search, param)
                value = value.isoformat() if hasattr(value, "isoformat") else value
            else:
                value = search.__dict__.get(param)
            if isinstance(value, models.Model):
                self.fields[param].initial = value.id
            else:
                self.fields[param].initial = value

            # Mark non-editable modified fields as hidden. That way, templates
            # rendering a form can just loop over hidden_fields to ensure that
            # all necessary search options are kept when submitting the form.
            if search.is_modified(param) and param not in editable_fields:
                self.fields[param].widget = forms.HiddenInput()


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            "theme",
            "bookmark_date_display",
            "bookmark_description_display",
            "bookmark_description_max_lines",
            "bookmark_link_target",
            "web_archive_integration",
            "tag_search",
            "tag_grouping",
            "enable_sharing",
            "enable_public_sharing",
            "enable_favicons",
            "enable_preview_images",
            "enable_automatic_html_snapshots",
            "display_url",
            "display_view_bookmark_action",
            "display_edit_bookmark_action",
            "display_archive_bookmark_action",
            "display_remove_bookmark_action",
            "permanent_notes",
            "default_mark_unread",
            "default_mark_shared",
            "custom_css",
            "auto_tagging_rules",
            "items_per_page",
            "sticky_pagination",
            "collapse_side_panel",
            "hide_bundles",
            "legacy_search",
        ]
        widgets = {
            "theme": FormSelect,
            "bookmark_date_display": FormSelect,
            "bookmark_description_display": FormSelect,
            "bookmark_description_max_lines": FormNumberInput,
            "bookmark_link_target": FormSelect,
            "web_archive_integration": FormSelect,
            "tag_search": FormSelect,
            "tag_grouping": FormSelect,
            "auto_tagging_rules": FormTextarea,
            "custom_css": FormTextarea,
            "items_per_page": FormNumberInput,
            "display_url": FormCheckbox,
            "permanent_notes": FormCheckbox,
            "display_view_bookmark_action": FormCheckbox,
            "display_edit_bookmark_action": FormCheckbox,
            "display_archive_bookmark_action": FormCheckbox,
            "display_remove_bookmark_action": FormCheckbox,
            "sticky_pagination": FormCheckbox,
            "collapse_side_panel": FormCheckbox,
            "hide_bundles": FormCheckbox,
            "legacy_search": FormCheckbox,
            "enable_favicons": FormCheckbox,
            "enable_preview_images": FormCheckbox,
            "enable_sharing": FormCheckbox,
            "enable_public_sharing": FormCheckbox,
            "enable_automatic_html_snapshots": FormCheckbox,
            "default_mark_unread": FormCheckbox,
            "default_mark_shared": FormCheckbox,
        }


class GlobalSettingsForm(forms.ModelForm):
    class Meta:
        model = GlobalSettings
        fields = ["landing_page", "guest_profile_user", "enable_link_prefetch"]
        widgets = {
            "landing_page": FormSelect,
            "guest_profile_user": FormSelect,
            "enable_link_prefetch": FormCheckbox,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["guest_profile_user"].empty_label = "Standard profile"
