"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import sys
from unittest.mock import MagicMock

# Mock external dependencies
sys.modules['xapian'] = MagicMock()

mock_conf = MagicMock()
mock_conf.XAPIAN_INDICES_DIR = "/tmp"
sys.modules['conf'] = MagicMock()
sys.modules['conf.xapian'] = mock_conf

from django.test import TestCase
from unittest.mock import patch, MagicMock
from search.views import _xapian_search


class DummyModelA:
    __name__ = "ModelA"
    search_key = "id"


class DummyModelB:
    __name__ = "ModelB"
    search_key = "id"


class SearchTestCase(TestCase):

    @patch("search.views.get_object_or_none")
    def test_search_returns_multiple_models(self, mock_get_obj):

        from search import views

        # Mock matches
        mock_match_1 = MagicMock()
        mock_match_1.document.get_data.return_value = "1"

        mock_match_2 = MagicMock()
        mock_match_2.document.get_data.return_value = "2"

        # Mock enquire behavior
        mock_enquire_1 = MagicMock()
        mock_enquire_1.get_mset.return_value = [mock_match_1]

        mock_enquire_2 = MagicMock()
        mock_enquire_2.get_mset.return_value = [mock_match_2]

        mock_qp = MagicMock()

        mock_db_1 = MagicMock()
        mock_db_1.get_doccount.return_value = 1

        mock_db_2 = MagicMock()
        mock_db_2.get_doccount.return_value = 1

        # Inject fake Xapian data
        views.Xapian_Enquires = {
            DummyModelA: (mock_db_1, mock_enquire_1, mock_qp),
            DummyModelB: (mock_db_2, mock_enquire_2, mock_qp),
        }

        # Mock object fetching
        mock_get_obj.side_effect = lambda model, **kwargs: {
            "model": model.__name__,
            "id": kwargs.get("id")
        }

        results = _xapian_search("test-query")

        # Assertions
        self.assertIn("DummyModelA", results)
        self.assertIn("DummyModelB", results)

        self.assertEqual(len(results["DummyModelA"]), 1)
        self.assertEqual(len(results["DummyModelB"]), 1)


class SearchViewResultPriorityTestCase(TestCase):
    """Regression tests for Issue #136: ineffective conditional in search()."""

    def setUp(self):
        from django.test import RequestFactory
        self.factory = RequestFactory()

    @patch("search.views.html_response")
    @patch("search.views._nav_panel_context", return_value={})
    @patch("search.views._xapian_search")
    def test_primary_search_preferred_when_has_results(
        self, mock_search, mock_nav, mock_html_response
    ):
        """When the space-preserved search returns results, those
        results should be used instead of the space-removed fallback."""
        from search.views import search

        # First call is the space-removed search (fallback "d"),
        # second call is the space-preserved search (primary "c").
        mock_search.side_effect = [
            {"App": ["fallback_result"]},   # d: removespace(query)
            {"App": ["primary_result"]},    # c: original query
        ]

        request = self.factory.get("/search/?q=gene+mania")
        response = search(request)

        # Ensure html_response was called with the primary results
        context = mock_html_response.call_args[0][1]
        self.assertEqual(context["results"], {"App": ["primary_result"]})
        self.assertEqual(context["search_query"], "gene mania")

    @patch("search.views.html_response")
    @patch("search.views._nav_panel_context", return_value={})
    @patch("search.views._xapian_search")
    def test_fallback_used_when_primary_search_empty(
        self, mock_search, mock_nav, mock_html_response
    ):
        """When the space-preserved search returns no results,
        the space-removed fallback should be used."""
        from search.views import search

        mock_search.side_effect = [
            {"App": ["fallback_result"]},   # d: removespace(query)
            {},                             # c: original query (empty)
        ]

        request = self.factory.get("/search/?q=gene+mania")
        response = search(request)

        # Ensure html_response was called with the fallback results
        context = mock_html_response.call_args[0][1]
        self.assertEqual(context["results"], {"App": ["fallback_result"]})
        self.assertEqual(context["search_query"], "genemania")