import base64
from types import SimpleNamespace

from backend import email_service


def _encode(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii")


# =========================================================================
# get_email_body unit tests – cover every realistic payload structure
# =========================================================================


def test_get_email_body_plain_text_single_part():
    """Simple single-part text/plain email (e.g. Gmail web plain-text compose)."""
    payload = {
        "mimeType": "text/plain",
        "body": {"data": _encode("I'd like to teach ECON 30223 at MWF 9:00am.")},
    }
    body = email_service.get_email_body(payload)
    assert "ECON 30223" in body
    assert "MWF 9:00am" in body


def test_get_email_body_html_only_single_part():
    """Single-part text/html email with no plain text alternative."""
    payload = {
        "mimeType": "text/html",
        "body": {
            "data": _encode(
                "<div>I prefer <b>ECON 10223</b> at TTh 11:00am.</div>"
            )
        },
    }
    body = email_service.get_email_body(payload)
    assert "ECON 10223" in body
    assert "TTh 11:00am" in body
    assert "<b>" not in body


def test_get_email_body_falls_back_to_html():
    """multipart/alternative with only an HTML part (no text/plain sibling)."""
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {
                "mimeType": "text/html",
                "body": {
                    "data": _encode(
                        "<div>Hello Professor,<br>I can teach <b>ECON 10223</b>.</div>"
                    )
                },
            }
        ],
    }

    body = email_service.get_email_body(payload)

    assert "Hello Professor" in body
    assert "ECON 10223" in body
    assert "<b>" not in body


def test_get_email_body_prefers_plain_over_html():
    """multipart/alternative with both text/plain and text/html – plain wins."""
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {
                "mimeType": "text/plain",
                "body": {"data": _encode("Plain version: ECON 20213")},
            },
            {
                "mimeType": "text/html",
                "body": {
                    "data": _encode(
                        "<p>HTML version: <b>ECON 20213</b></p>"
                    )
                },
            },
        ],
    }
    body = email_service.get_email_body(payload)
    assert body == "Plain version: ECON 20213"
    assert "<b>" not in body


def test_get_email_body_nested_multipart_mixed():
    """Deeply nested multipart/mixed → multipart/alternative (Outlook w/ attachment)."""
    payload = {
        "mimeType": "multipart/mixed",
        "parts": [
            {
                "mimeType": "multipart/alternative",
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {"data": _encode("Nested plain: ECON 40223")},
                    },
                    {
                        "mimeType": "text/html",
                        "body": {
                            "data": _encode(
                                "<div>Nested html: ECON 40223</div>"
                            )
                        },
                    },
                ],
            },
            {
                "mimeType": "application/pdf",
                "filename": "syllabus.pdf",
                "body": {"attachmentId": "ANGjdJ8..."},
            },
        ],
    }
    body = email_service.get_email_body(payload)
    assert "Nested plain: ECON 40223" in body
    # Should use plain text, not HTML
    assert "<div>" not in body


def test_get_email_body_nested_html_only():
    """multipart/mixed wrapping multipart/alternative with only HTML (no plain)."""
    payload = {
        "mimeType": "multipart/mixed",
        "parts": [
            {
                "mimeType": "multipart/alternative",
                "parts": [
                    {
                        "mimeType": "text/html",
                        "body": {
                            "data": _encode(
                                "<p>I&#39;d like MWF 10:00&ndash;10:50am for <em>Intro Macro</em>.</p>"
                            )
                        },
                    },
                ],
            },
        ],
    }
    body = email_service.get_email_body(payload)
    assert "Intro Macro" in body
    assert "I'd like" in body  # HTML entity decoded
    assert "<p>" not in body
    assert "<em>" not in body


def test_get_email_body_empty_plain_falls_back_to_html():
    """text/plain part exists but is blank → should use the HTML part."""
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {
                "mimeType": "text/plain",
                "body": {"data": _encode("   ")},  # whitespace-only
            },
            {
                "mimeType": "text/html",
                "body": {
                    "data": _encode("<div>Actual content here</div>")
                },
            },
        ],
    }
    body = email_service.get_email_body(payload)
    assert "Actual content here" in body


def test_get_email_body_empty_payload():
    """Totally empty payload returns empty string, no crash."""
    payload = {"mimeType": "multipart/mixed", "parts": []}
    body = email_service.get_email_body(payload)
    assert body == ""


# =========================================================================
# Fake DB / Gmail helpers for poll_unread_replies tests
# =========================================================================


class _FakeQuery:
    def __init__(self, model_name: str, db):
        self.model_name = model_name
        self.db = db
        self._filters = {}

    def filter(self, *args, **kwargs):
        self._filters.update(kwargs)
        return self

    def first(self):
        if self.model_name == "Professor":
            return self.db.professor
        if self.model_name == "EmailLog":
            return self.db._email_log_result
        if self.model_name == "Preference":
            return None
        return None


class _FakeDB:
    def __init__(self, *, email_log_result=None):
        self.professor = SimpleNamespace(id=7, email="prof@tcu.edu")
        self.added = []
        self.commits = 0
        self._email_log_result = email_log_result

    def query(self, model):
        return _FakeQuery(model.__name__, self)

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass

    def close(self):
        pass


class _FakeExecute:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload


class _FakeMessagesAPI:
    def __init__(self, message_payloads):
        self.message_payloads = message_payloads
        self.modified_ids = []
        self._list_calls = 0

    def list(self, **kwargs):
        self._list_calls += 1
        if self._list_calls == 1:
            msg_ids = list(self.message_payloads.keys())
            first_batch = [{"id": msg_ids[0], "threadId": "t1"}]
            resp = {"messages": first_batch}
            if len(msg_ids) > 1:
                resp["nextPageToken"] = "page-2"
            return _FakeExecute(resp)
        # Second page: remaining messages
        msg_ids = list(self.message_payloads.keys())
        return _FakeExecute(
            {"messages": [{"id": mid, "threadId": f"t{i+2}"} for i, mid in enumerate(msg_ids[1:])]}
        )

    def get(self, userId, id, format):
        return _FakeExecute(self.message_payloads[id])

    def modify(self, userId, id, body):
        self.modified_ids.append(id)
        return _FakeExecute({})


class _SinglePageMessagesAPI(_FakeMessagesAPI):
    """Returns all messages in a single page – simpler for single-message tests."""

    def __init__(self, message_payloads, thread_ids=None):
        super().__init__(message_payloads)
        self._thread_ids = thread_ids or {}

    def list(self, **kwargs):
        msgs = []
        for mid in self.message_payloads:
            tid = self._thread_ids.get(mid, mid)
            msgs.append({"id": mid, "threadId": tid})
        return _FakeExecute({"messages": msgs})


class _FakeUsersAPI:
    def __init__(self, messages_api):
        self._messages = messages_api

    def messages(self):
        return self._messages


class _FakeService:
    def __init__(self, messages_api):
        self._users = _FakeUsersAPI(messages_api)

    def users(self):
        return self._users


# =========================================================================
# poll_unread_replies integration tests
# =========================================================================


def test_poll_unread_replies_processes_multiple_messages(monkeypatch):
    message_payloads = {
        "m1": {
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Re: Action Required: Fall 2027 Teaching Preferences"},
                    {"name": "From", "value": "Prof <prof@tcu.edu>"},
                    {"name": "X-Scheduler-Token", "value": "PROF-7-Fall-2027"},
                ],
                "mimeType": "text/plain",
                "body": {"data": _encode("First response")},
            }
        },
        "m2": {
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Re: Action Required: Fall 2027 Teaching Preferences"},
                    {"name": "From", "value": "Prof <prof@tcu.edu>"},
                    {"name": "X-Scheduler-Token", "value": "PROF-7-Fall-2027"},
                ],
                "mimeType": "text/html",
                "body": {"data": _encode("<div>Second response</div>")},
            }
        },
    }

    fake_db = _FakeDB()
    msgs_api = _FakeMessagesAPI(message_payloads)
    fake_service = _FakeService(msgs_api)

    monkeypatch.setattr(email_service, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(email_service, "get_gmail_service", lambda server_mode=False: fake_service)

    replies = email_service.poll_unread_replies(server_mode=True)

    assert len(replies) == 2
    assert [reply["subject"] for reply in replies] == [
        "Re: Action Required: Fall 2027 Teaching Preferences",
        "Re: Action Required: Fall 2027 Teaching Preferences",
    ]
    assert msgs_api.modified_ids == ["m1", "m2"]


def test_poll_reply_without_token_matches_via_thread_id(monkeypatch):
    """Realistic reply: no X-Scheduler-Token header, matched via EmailLog thread_id (Strategy B)."""
    message_payloads = {
        "m1": {
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Re: Action Required: Fall 2027 Teaching Preferences"},
                    {"name": "From", "value": "Prof <prof@tcu.edu>"},
                    # NOTE: No X-Scheduler-Token — this is realistic for actual replies
                ],
                "mimeType": "multipart/alternative",
                "parts": [
                    {
                        "mimeType": "text/html",
                        "body": {
                            "data": _encode(
                                "<div>I'd like to teach ECON 30223 at MWF 11am.</div>"
                            )
                        },
                    }
                ],
            }
        },
    }

    # Simulate a sent EmailLog that matches the thread_id
    sent_log = SimpleNamespace(
        professor_id=7,
        subject="Action Required: Fall 2027 Teaching Preferences",
    )
    fake_db = _FakeDB(email_log_result=sent_log)
    msgs_api = _SinglePageMessagesAPI(message_payloads, thread_ids={"m1": "thread-abc"})
    fake_service = _FakeService(msgs_api)

    monkeypatch.setattr(email_service, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(email_service, "get_gmail_service", lambda server_mode=False: fake_service)

    replies = email_service.poll_unread_replies(server_mode=True)

    assert len(replies) == 1
    assert replies[0]["professor_id"] == 7
    assert replies[0]["semester"] == "Fall"
    assert replies[0]["year"] == 2027

    # Verify body was saved to a Preference record
    prefs_added = [obj for obj in fake_db.added if hasattr(obj, "raw_email")]
    assert len(prefs_added) == 1
    assert "ECON 30223" in prefs_added[0].raw_email
    assert "<div>" not in prefs_added[0].raw_email  # HTML stripped


def test_poll_html_reply_body_saved_to_preference(monkeypatch):
    """Verify the HTML body is correctly extracted and saved into pref.raw_email."""
    html_content = (
        "<html><body>"
        "<p>Dear Scheduling,</p>"
        "<p>I would like:</p>"
        "<ul>"
        "<li>ECON 10223 Intro Micro, MWF 8:00-8:50am</li>"
        "<li>ECON 30223 Intermediate Micro, TTh 2:00-3:20pm</li>"
        "</ul>"
        "<p>No Fridays please.</p>"
        "</body></html>"
    )
    message_payloads = {
        "m1": {
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Re: Action Required: Fall 2027 Teaching Preferences"},
                    {"name": "From", "value": "Prof <prof@tcu.edu>"},
                    {"name": "X-Scheduler-Token", "value": "PROF-7-Fall-2027"},
                ],
                "mimeType": "text/html",
                "body": {"data": _encode(html_content)},
            }
        },
    }

    fake_db = _FakeDB()
    msgs_api = _SinglePageMessagesAPI(message_payloads)
    fake_service = _FakeService(msgs_api)

    monkeypatch.setattr(email_service, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(email_service, "get_gmail_service", lambda server_mode=False: fake_service)

    replies = email_service.poll_unread_replies(server_mode=True)

    assert len(replies) == 1

    prefs_added = [obj for obj in fake_db.added if hasattr(obj, "raw_email")]
    assert len(prefs_added) == 1
    raw = prefs_added[0].raw_email
    # All key info should be present in the extracted text
    assert "ECON 10223" in raw
    assert "ECON 30223" in raw
    assert "MWF 8:00-8:50am" in raw
    assert "No Fridays" in raw
    # No HTML tags should remain
    assert "<p>" not in raw
    assert "<li>" not in raw
    assert "<ul>" not in raw

