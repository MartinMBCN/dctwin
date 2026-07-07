from __future__ import annotations

from dctwin.adapters.text_cv import adapt_cv_text


def test_pasted_cv_text_is_cv_source_with_redacted_enrollment_candidate() -> None:
    result = adapt_cv_text(
        "Alex Example\nalex@example.com\nLed platform delivery.",
        label="Manually entered CV, July 7 2026, 10:34 CEST",
    )

    assert result.model_document["source_type"] == "cv"
    assert result.model_document["media_type"] == "text/plain"
    assert result.model_document["adapter"]["name"] == "text_cv"
    assert any("[EMAIL_1]" in block["text"] for block in result.model_document["blocks"])
    assert result.enrollment_document["candidates"][0]["value"] == "alex@example.com"
    assert "alex@example.com" not in repr(result)
