from concierge.gates.authorise import authorise
from concierge.skills import book_appointment, fetch_balance, print_statement, update_contact_details
from concierge.tools import find_slots, knowledge, opening_hours
from tests.conftest import result


def test_print_statement_for_own_account(runtime):
    r = result(print_statement.func(account_id="ACC-7783", period_months=3, runtime=runtime()))
    assert r["status"] == "done" and r["risk"] == "low"
    assert "ACC-7783" in r["result"] and "STM-" in r["result"]


def test_print_statement_refuses_another_customers_account(runtime):
    r = result(print_statement.func(account_id="ACC-7781", period_months=3, runtime=runtime("C1003")))
    assert r["status"] == "refused"
    assert "does not belong" in r["result"]


def test_fetch_balance_formats_negative_balance(runtime):
    r = result(fetch_balance.func(account_id="ACC-7784", runtime=runtime("C1004")))
    assert r["result"] == "Available balance on ACC-7784: -£120.40."


def test_skills_refuse_without_identified_customer(runtime):
    r = result(fetch_balance.func(account_id="ACC-7783", runtime=runtime(None)))
    assert r["status"] == "refused" and "No identified customer" in r["result"]


def test_book_appointment(runtime):
    r = result(book_appointment.func(appointment_type="mortgage adviser", preferred_time=None, runtime=runtime()))
    assert r["status"] == "done" and "next available slot" in r["result"] and "APT-" in r["result"]


def test_update_contact_details_keeps_previous_value(runtime):
    r = result(update_contact_details.func(field="phone", new_value="+44 7700 900999", runtime=runtime()))
    assert r["risk"] == "medium"
    assert "previous value, +44 7700 900103, would be kept for 30 days" in r["result"]
    assert "simulated" in r["result"]


def test_update_contact_details_schema_only_allows_phone_or_email():
    schema = update_contact_details.args_schema.model_json_schema()
    assert schema["properties"]["field"]["enum"] == ["phone", "email"]


def test_unknown_capability_is_refused():
    auth = authorise("close_account", "C1003")
    assert not auth.authorised and auth.risk == "high"


def test_read_only_tools():
    assert opening_hours.invoke({"day": "Saturday"}).startswith("Saturday: 09:00 to 13:00")
    assert "mortgage adviser slots" in find_slots.invoke({"appointment_type": "mortgage adviser"})
    assert "Mortgages" in knowledge.invoke({"query": "mortgage documents to bring"})
    assert knowledge.invoke({"query": "zzz qqq"}).startswith("No matching section")


def test_contact_values_are_validated_before_approval():
    import pytest
    from pydantic import ValidationError

    from concierge.skills.update_contact_details import UpdateContactDetailsInput

    for field, value in [("phone", ""), ("phone", "12"), ("email", "not an email"), ("email", "  ")]:
        with pytest.raises(ValidationError):
            UpdateContactDetailsInput(field=field, new_value=value)
    assert UpdateContactDetailsInput(field="email", new_value=" ben@example.com ").new_value == "ben@example.com"
    assert UpdateContactDetailsInput(field="phone", new_value="+44 7700 900999").new_value == "+44 7700 900999"
