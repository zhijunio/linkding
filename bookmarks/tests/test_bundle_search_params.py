"""Tests for Bundle search_params (secondary filters)."""

from django.test import TestCase

from bookmarks.models import BookmarkBundle, BookmarkSearch
from bookmarks.queries import query_bookmarks
from bookmarks.tests.helpers import BookmarkFactoryMixin


class BundleSearchParamsTestCase(TestCase, BookmarkFactoryMixin):
    def setUp(self):
        self.user = self.get_or_create_test_user()
        self.profile = self.user.profile

    def test_bundle_search_params_date_relative(self):
        """Bundle search_params date filter (relative period)."""
        from datetime import timedelta

        from django.utils import timezone

        now = timezone.now()
        self.setup_bookmark(
            user=self.user,
            title="Old",
            added=now - timedelta(days=10),
        )
        self.setup_bookmark(user=self.user, title="Recent")
        bundle = self.setup_bundle(
            user=self.user,
            search="",
            search_params={
                "date_filter_by": BookmarkSearch.FILTER_DATE_BY_ADDED,
                "date_filter_type": BookmarkSearch.FILTER_DATE_TYPE_RELATIVE,
                "date_filter_relative_string": "last_7_days",
            },
        )
        search = BookmarkSearch(bundle=bundle)
        results = list(query_bookmarks(self.user, self.profile, search))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Recent")

    def test_bundle_search_params_tagged_untagged(self):
        """Bundle search_params tagged=no filters for bookmarks with no tags."""
        self.setup_bookmark(user=self.user, tags=[self.setup_tag()])
        self.setup_bookmark(user=self.user, title="No tags")
        bundle = self.setup_bundle(
            user=self.user,
            search="",
            search_params={"tagged": BookmarkSearch.FILTER_TAGGED_UNTAGGED},
        )
        search = BookmarkSearch(bundle=bundle)
        results = list(query_bookmarks(self.user, self.profile, search))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "No tags")

    def test_bundle_filter_unread_backward_compat(self):
        """filter_unread still works when search_params empty."""
        self.setup_bookmark(user=self.user, unread=True)
        self.setup_bookmark(user=self.user, unread=False, title="Read")
        bundle = self.setup_bundle(
            user=self.user,
            search="",
            filter_unread=BookmarkBundle.FILTER_STATE_YES,
        )
        search = BookmarkSearch(bundle=bundle)
        results = list(query_bookmarks(self.user, self.profile, search))
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].unread)
