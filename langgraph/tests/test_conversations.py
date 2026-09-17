from langgraph.checkpoint.memory import InMemorySaver

from concierge.conversations import cases, run_case
from concierge.graph import build_graph
from tests.conftest import ScriptedModel, say


def test_repeating_a_case_starts_a_fresh_thread(tmp_path, monkeypatch):
    monkeypatch.setenv("CONCIERGE_DECISIONS_DB", str(tmp_path / "decisions.sqlite"))
    graph = build_graph(
        ScriptedModel(responses=[say("We close at 13:00 on Saturday."), say("We close at 13:00 on Saturday.")]),
        classifier=None,
        checkpointer=InMemorySaver(),
    )
    t02 = next(c for c in cases() if c["test_id"] == "T02")
    first = run_case(graph, t02, session="experiment")
    second = run_case(graph, t02, session="experiment")
    # One customer turn each: the second run did not inherit the first conversation.
    assert len(first.state["transcript"]) == 2
    assert len(second.state["transcript"]) == 2
