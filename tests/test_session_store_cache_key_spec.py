from app.data.session_store import SessionStore, _analysis_cache_key


def test_analysis_cache_key_changes_when_spec_changes():
    base_args = {
        "selected_features": ["Volume"],
        "batch": "全部 (All)",
        "refdes": "全部 (All)",
        "part_type": "全部 (All)",
    }
    spec_a = {"volume": {"usl": 120, "lsl": 80, "target": 100}}
    spec_b = {"volume": {"usl": 130, "lsl": 70, "target": 100}}
    token_a = SessionStore.spec_cache_token(spec_a)
    token_b = SessionStore.spec_cache_token(spec_b)
    key_a = _analysis_cache_key(**base_args, spec_version=token_a)
    key_b = _analysis_cache_key(**base_args, spec_version=token_b)
    assert key_a != key_b
