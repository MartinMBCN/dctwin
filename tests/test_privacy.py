from dctwin.privacy import minimize_direct_identifiers


def test_direct_identifiers_are_removed_without_retaining_values() -> None:
    original = "Alex | alex@example.com | +34 612 345 678 | 10 Example Street"
    minimized, redactions = minimize_direct_identifiers(original)

    assert "alex@example.com" not in minimized
    assert "+34 612 345 678" not in minimized
    assert "10 Example Street" not in minimized
    assert "[EMAIL_1]" in minimized
    assert "[PHONE_1]" in minimized
    assert "[STREET_ADDRESS_1]" in minimized
    assert {item.category for item in redactions} == {"email", "phone", "street_address"}
    assert all("example.com" not in repr(item) for item in redactions)
    assert next(item.value for item in redactions if item.category == "email") == "alex@example.com"
