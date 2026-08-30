from datetime import UTC, datetime

from app.services.identity import link_first_login


class _Member:
    def __init__(self) -> None:
        self.email = "caregiver@example.com"
        self.login_status = "pending"
        self.auth_subject = None
        self.first_login_at = None


def test_pending_member_links_on_case_insensitive_email() -> None:
    member = _Member()
    now = datetime(2026, 8, 19, tzinfo=UTC)
    linked = link_first_login(
        member, subject="sub-abc", email="Caregiver@Example.com", now=now
    )
    assert linked.login_status == "linked"
    assert linked.auth_subject == "sub-abc"
    assert linked.first_login_at == now


def test_already_linked_member_is_unchanged_for_other_subject() -> None:
    member = _Member()
    member.login_status = "linked"
    member.auth_subject = "sub-original"
    result = link_first_login(
        member,
        subject="sub-other",
        email="caregiver@example.com",
        now=datetime.now(UTC),
    )
    assert result.auth_subject == "sub-original"


def test_email_mismatch_does_not_link() -> None:
    member = _Member()
    result = link_first_login(
        member, subject="sub-abc", email="other@example.com", now=datetime.now(UTC)
    )
    assert result.login_status == "pending"
    assert result.auth_subject is None


def test_none_login_status_does_not_link() -> None:
    member = _Member()
    member.login_status = "none"
    result = link_first_login(
        member, subject="sub-abc", email="caregiver@example.com", now=datetime.now(UTC)
    )
    assert result.login_status == "none"
