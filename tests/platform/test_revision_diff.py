from referee.comparison import revision_diff

def test_revision_diff_counts_change():
    d=revision_diff('a\nb','a\nc')
    assert d['added_lines']==1 and d['removed_lines']==1
