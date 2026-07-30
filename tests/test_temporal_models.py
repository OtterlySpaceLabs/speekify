from speekify.temporal_client import build_workflow_input
from speekify.temporal_models import GenerationOptionsV1, canonical_json, fingerprint
from speekify.workflow import GenerationRequest


def test_canonical_fingerprint_is_order_independent() -> None:
    assert fingerprint({"b": 2, "a": 1}) == fingerprint({"a": 1, "b": 2})


def test_temporal_options_are_json_serializable() -> None:
    options = GenerationOptionsV1(
        voice="M5",
        language_code="en",
        speed=1.0,
        steps=10,
        output_dir="/tmp",
    )

    assert '"voice":"M5"' in canonical_json(options)


def test_workflow_input_keeps_inline_text_out_of_temporal_history(tmp_path) -> None:
    secret_text = "Private text with bearer secret-value"
    request = GenerationRequest(
        source_text=secret_text,
        voice="M5",
        language_code="en",
        speed=1.0,
        steps=10,
        output_dir=tmp_path,
    )

    payload = build_workflow_input(request, data_dir=tmp_path / "data", verbose=False)
    serialized = canonical_json(payload)

    assert secret_text not in serialized
    assert payload.source.value == ""
    assert payload.source.display_name == f"inline text ({len(secret_text)} characters)"
    assert payload.source.payload_path
    assert payload.source.payload_sha256
    assert secret_text in (
        (tmp_path / "data" / "jobs" / payload.job_id / "source.json").read_text(
            encoding="utf-8"
        )
    )


def test_forced_url_rejects_embedded_credentials(tmp_path) -> None:
    request = GenerationRequest(
        source_text="https://user:password@example.com/article",
        voice="M5",
        language_code="en",
        speed=1.0,
        steps=10,
        output_dir=tmp_path,
        is_url_mode=True,
    )

    try:
        build_workflow_input(request, data_dir=tmp_path / "data", verbose=False)
    except ValueError as exc:
        assert "credentials" in str(exc)
    else:
        raise AssertionError("Credential-bearing URL should be rejected")


def test_workflow_input_keeps_full_file_path_out_of_temporal_history(tmp_path) -> None:
    source_path = tmp_path / "private" / "notes.txt"
    source_path.parent.mkdir()
    source_path.write_text("Private notes", encoding="utf-8")
    request = GenerationRequest(
        source_text=str(source_path),
        voice="M5",
        language_code="en",
        speed=1.0,
        steps=10,
        output_dir=tmp_path,
    )

    payload = build_workflow_input(request, data_dir=tmp_path / "data", verbose=False)

    assert str(source_path) not in canonical_json(payload)
    assert payload.source.value == "notes.txt"
    assert payload.source.content_sha256
    assert payload.source.payload_sha256
