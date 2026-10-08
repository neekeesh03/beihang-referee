from referee.config import ReviewConfig
from referee.profiles import ProfileRegistry


def test_builtin_profiles_present_and_loadable():
    reg = ProfileRegistry()
    assert {"balanced", "editorial-screen", "full-audit", "reproducibility", "revision-closure"}.issubset(set(reg.names()))
    cfg = ReviewConfig.from_profile("full-audit", run_root="runs-test", model="fixture-model")
    assert cfg.mode == "exhaustive"
    assert cfg.run_root == "runs-test"
    assert cfg.model == "fixture-model"
