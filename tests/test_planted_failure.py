def test_planted_failure():
    # Scratch PR: proves the required "test" check blocks a merge. Never merged.
    assert False, "planted failure"
