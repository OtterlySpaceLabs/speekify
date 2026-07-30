from pathlib import Path

from speekify.job_store import (
    atomic_write_json,
    deterministic_output_path,
    finalize_diagnostic_report,
    read_json,
    redact_text,
)
from speekify.temporal_models import DiagnosticReportInputV1, FailureEnvelopeV1


def test_atomic_write_json_replaces_complete_object(tmp_path: Path) -> None:
    target = tmp_path / "state.json"
    atomic_write_json(target, {"state": "first"})
    atomic_write_json(target, {"state": "second"})

    assert read_json(target) == {"state": "second"}
    assert not list(tmp_path.glob("*.tmp"))


def test_deterministic_output_path_is_stable(tmp_path: Path) -> None:
    first = deterministic_output_path(
        tmp_path,
        "Résumé du jour",
        "2026-07-30T12:34:56+00:00",
        "abcdef1234567890",
    )
    second = deterministic_output_path(
        tmp_path,
        "Résumé du jour",
        "2026-07-30T12:34:56+00:00",
        "abcdef1234567890",
    )

    assert first == second
    assert first.name == "resume-du-jour-20260730-123456-1234567890.wav"


def test_redaction_removes_url_secrets_and_tokens() -> None:
    redacted = redact_text(
        "GET https://user:pass@example.com/a?token=secret#fragment "
        "Authorization: Bearer abc.def and api_key=hunter2"
    )

    assert "secret" not in redacted
    assert "hunter2" not in redacted
    assert "abc.def" not in redacted
    assert "https://example.com/a" in redacted


def test_diagnostic_report_is_local_redacted_and_atomic(tmp_path: Path) -> None:
    report = finalize_diagnostic_report(
        DiagnosticReportInputV1(
            scope="generation",
            identifier="job-1",
            data_dir=str(tmp_path),
            reason="failure",
            outcome="failed",
            source_display_name="https://example.com/a?token=secret",
            failures=[
                FailureEnvelopeV1(
                    code="FetchError",
                    category="network",
                    stage="preparing",
                    retryable=True,
                    message="Authorization: Bearer private-token",
                )
            ],
        )
    )

    content = Path(report.path).read_text(encoding="utf-8")
    assert "Speekify diagnostic report" in content
    assert "secret" not in content
    assert "private-token" not in content
    assert report.sha256
