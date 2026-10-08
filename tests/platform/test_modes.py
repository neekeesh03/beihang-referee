from referee.modes import ReviewModeRegistry

def test_modes_include_revision_rebuttal():
    names=ReviewModeRegistry().names()
    assert 'revision' in names and 'rebuttal' in names and 'meta_review' in names
