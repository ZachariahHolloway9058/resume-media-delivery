from resume_ingestion.resume_pipeline import decide_delivery


def test_complete_resume_is_ready_for_creator_delivery() -> None:
    text = """Ada Lovelace
ada@example.org
Experience building Python and SQL data systems
"""

    decision = decide_delivery(text)

    assert decision.status == "ready_for_delivery"
    assert decision.fields.name == "Ada Lovelace"
    assert decision.fields.email == "ada@example.org"
    assert decision.fields.skills == ["Python", "SQL"]


def test_resume_without_contact_is_routed_to_review() -> None:
    decision = decide_delivery("Grace Hopper\nPython compiler engineering")

    assert decision.status == "needs_review"
    assert decision.fields.name == "Grace Hopper"

