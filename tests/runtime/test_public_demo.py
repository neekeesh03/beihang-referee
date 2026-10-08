from __future__ import annotations

import json
from pathlib import Path

from referee.config import ReviewConfig
from referee.engine import ReviewEngine
from referee.providers.scripted import ScriptedLLMProvider, ScriptedSearchProvider


def test_public_offline_demo_fixture_runs(tmp_path):
    root = Path(__file__).resolve().parents[2]
    responses = json.loads((root / "examples" / "demo_responses.json").read_text(encoding="utf-8"))
    cfg = ReviewConfig(
        mode="standard",
        pipeline="core",
        run_root=str(tmp_path / "runs"),
        enable_literature_search=False,
    )
    engine = ReviewEngine(
        llm=ScriptedLLMProvider(responses),
        search=ScriptedSearchProvider(),
        config=cfg,
        package_root=str(root),
    )

    import asyncio

    state = asyncio.run(engine.review([str(root / "examples" / "demo_manuscript.md")], run_id="public-demo"))
    assert state.final_review_exportable is True
    assert len(state.admitted_concerns) == 1
    assert state.admitted_concerns[0]["title"] == "The design does not identify the headline causal effect"
