import contextlib
from types import SimpleNamespace
from unittest.mock import patch

from odoo.tests import tagged

from ..tracing.runner import _execute, _run_error
from ..tracing.session import TraceSession
from ..tracing.targets import get_index
from .common import TraceCase

CALL_ERROR = {"type": "builtins.ValueError", "message": "boom"}


def _session(*, failure=None, truncated=False, max_steps=10):
    """Only what _run_error reads of a TraceSession."""
    return SimpleNamespace(failure=failure, truncated=truncated, max_steps=max_steps)


@tagged("post_install", "-at_install")
class TestRunError(TraceCase):
    """Which error a trace reports, in order of precedence."""

    def test_a_clean_run_has_no_error(self):
        self.assertIsNone(_run_error(_session(), None, []))

    def test_a_recorder_failure_wins_over_everything(self):
        error = _run_error(
            _session(failure=RuntimeError("stack"), truncated=True), CALL_ERROR, ["commit"]
        )

        self.assertEqual(error["type"], "flow_tracer.RecorderError")
        self.assertEqual(error["message"], "Recording failed: RuntimeError('stack')")

    def test_the_call_error_wins_over_refused_commits_and_truncation(self):
        self.assertEqual(_run_error(_session(truncated=True), CALL_ERROR, ["commit"]), CALL_ERROR)

    def test_refused_commits_are_counted(self):
        once = _run_error(_session(), None, ["commit"])
        twice = _run_error(_session(), None, ["commit", "commit"])

        self.assertEqual(once["type"], "flow_tracer.CommitRefused")
        self.assertIn("tried to commit 1 time during", once["message"])
        self.assertIn("tried to commit 2 times during", twice["message"])

    def test_refused_commits_win_over_truncation(self):
        error = _run_error(_session(truncated=True), None, ["commit"])

        self.assertEqual(error["type"], "flow_tracer.CommitRefused")

    def test_truncation_names_the_limit(self):
        error = _run_error(_session(truncated=True, max_steps=3), None, [])

        self.assertEqual(error["type"], "flow_tracer.TraceTruncated")
        self.assertIn("after 3 steps", error["message"])


@tagged("post_install", "-at_install")
class TestExecute(TraceCase):
    """Calling the method under the recorder, inside a savepoint."""

    def setUp(self):
        super().setUp()
        self.contact = self.admin_env["res.partner"].create(
            {"name": "Ada Lovelace", "company_name": "Analytical Engines Ltd"}
        )

    def execute(self, *, dry_run=True):
        index = get_index(self.admin_env.registry)
        session = TraceSession(index)
        result = _execute(
            self.admin_env, self.contact, "create_company", {}, session, index, dry_run
        )
        self.env.invalidate_all()
        return result, session

    def test_a_dry_run_is_recorded_and_rolled_back(self):
        (error, commit_attempts), session = self.execute()

        self.assertIsNone(error)
        self.assertEqual(commit_attempts, [])
        self.assertTrue(session.steps)
        self.assertFalse(self.contact.parent_id)

    def test_a_real_run_keeps_its_changes(self):
        (error, _), _ = self.execute(dry_run=False)

        self.assertIsNone(error)
        self.assertEqual(self.contact.parent_id.name, "Analytical Engines Ltd")

    def test_a_failing_call_returns_its_error_and_is_rolled_back(self):
        def write_then_fail(records):
            records.write({"name": "renamed"})
            raise ValueError("boom")

        with patch.object(type(self.contact), "create_company", write_then_fail):
            (error, _), _ = self.execute(dry_run=False)

        self.assertEqual(error, CALL_ERROR)
        self.assertEqual(self.contact.name, "Ada Lovelace")

    def test_a_swallowed_commit_is_returned_as_attempt(self):
        def committing_quietly(records):
            with contextlib.suppress(Exception):  # what the code under trace does
                records.env.cr.commit()
            return True

        with patch.object(type(self.contact), "create_company", committing_quietly):
            (error, commit_attempts), _ = self.execute()

        self.assertIsNone(error)
        self.assertEqual(commit_attempts, ["commit"])
