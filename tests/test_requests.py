import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]

_IMPORT_ERROR = None
flask_app = None
create_title_request_api = None
try:
    from app.app import app as flask_app
    from app.app import create_title_request_api
except ModuleNotFoundError as exc:
    _IMPORT_ERROR = exc


class _FakeUser:
    def __init__(self, user_id=1, is_admin=True):
        self.id = user_id
        self.is_admin = is_admin
        self.is_authenticated = True

    def has_access(self, access):
        return access in {"shop", "admin", "backup"}


class RequestFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if _IMPORT_ERROR is not None:
            raise unittest.SkipTest(f"Missing dependency for request tests: {_IMPORT_ERROR}")

    def _invoke_create_request(self, payload, create_result=None):
        fake_user = _FakeUser(user_id=17, is_admin=True)
        with flask_app.test_request_context("/api/requests", method="POST", json=payload):
            with patch("app.auth.admin_account_created", return_value=True), patch("app.auth.current_user", fake_user), patch("app.app.current_user", fake_user):
                if create_result is None:
                    response = create_title_request_api()
                    create_mock = None
                else:
                    with patch("app.app.create_title_request", return_value=create_result) as create_mock:
                        response = create_title_request_api()

        if isinstance(response, tuple):
            response, status_code = response
        else:
            status_code = response.status_code
        return response.get_json(), status_code, create_mock

    def test_create_request_api_accepts_manual_title_id_without_name(self):
        data, status_code, create_mock = self._invoke_create_request(
            {"title_id": "0100B6E012EBE000"},
            (True, "Request created.", SimpleNamespace(id=31)),
        )

        self.assertEqual(status_code, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["request_id"], 31)
        self.assertEqual(data["message"], "Request created.")
        create_mock.assert_called_once_with(17, "0100B6E012EBE000", title_name=None)

    def test_create_request_api_accepts_manual_title_id_with_name(self):
        data, status_code, create_mock = self._invoke_create_request(
            {"title_id": "0100C62011050000", "title_name": "Example Title"},
            (True, "Request created.", SimpleNamespace(id=44)),
        )

        self.assertEqual(status_code, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["request_id"], 44)
        create_mock.assert_called_once_with(17, "0100C62011050000", title_name="Example Title")

    def test_create_request_api_is_idempotent_for_duplicate_open_request(self):
        data, status_code, create_mock = self._invoke_create_request(
            {"title_id": "0100C62011050000", "title_name": "Example Title"},
            (True, "Request already exists.", SimpleNamespace(id=44)),
        )

        self.assertEqual(status_code, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["message"], "Request already exists.")
        self.assertEqual(data["request_id"], 44)
        create_mock.assert_called_once_with(17, "0100C62011050000", title_name="Example Title")

    def test_create_request_api_rejects_invalid_title_id(self):
        data, status_code, create_mock = self._invoke_create_request({"title_id": "1234"})

        self.assertEqual(status_code, 400)
        self.assertFalse(data["success"])
        self.assertEqual(data["message"], "Title ID must be 16 characters")
        self.assertIsNone(create_mock)


class RequestTemplateRegressionTests(unittest.TestCase):
    def test_requests_template_includes_admin_add_request_controls(self):
        content = (REPO_ROOT / "app" / "templates" / "requests.html").read_text(encoding="utf-8")

        self.assertIn('id="adminRequestSearchBox" name="admin-request-search" list="adminRequestSearchSuggestions"', content)
        self.assertIn('autocomplete="new-password" autocapitalize="off" autocorrect="off" spellcheck="false"', content)
        self.assertIn('id="adminRequestSearchSuggestions"', content)
        self.assertIn('id="adminRequestSearchResults"', content)
        self.assertIn('id="adminSelectedTitleText"', content)
        self.assertIn('id="adminSubmitRequestBtn"', content)
        self.assertIn("function updateAdminSearchSuggestions(results) {", content)
        self.assertIn("const filteredResults = (results || []).filter(item => item && item.in_library !== true);", content)
        self.assertIn("function handleAdminSearchSelection() {", content)
        self.assertIn("let adminSelectedTitle = null;", content)
        self.assertIn("if (!adminSelectedTitle || !adminSelectedTitle.id) {", content)
        self.assertIn("document.getElementById('adminRequestSearchBox')?.addEventListener('input', handleAdminSearchInput);", content)
        self.assertIn("document.getElementById('adminRequestSearchBox')?.addEventListener('change', handleAdminSearchSelection);", content)
        self.assertIn("document.getElementById('adminSubmitRequestBtn')?.addEventListener('click', submitAdminRequest);", content)
        self.assertIn("document.getElementById('adminSubmitRequestBtn')?.setAttribute('disabled', 'true');", content)
        self.assertNotIn('id="adminManualTitleId"', content)
        self.assertNotIn('id="adminManualTitleName"', content)

    def test_requests_template_keeps_end_user_request_controls(self):
        content = (REPO_ROOT / "app" / "templates" / "requests.html").read_text(encoding="utf-8")

        self.assertIn('id="requestSearchBox"', content)
        self.assertIn('id="requestSearchResults"', content)
        self.assertIn('id="submitRequestBtn"', content)
        self.assertIn("document.getElementById('requestSearchBox')?.addEventListener('input', handleUserSearchInput);", content)
        self.assertIn("document.getElementById('submitRequestBtn')?.addEventListener('click', submitRequest);", content)


if __name__ == "__main__":
    unittest.main()
