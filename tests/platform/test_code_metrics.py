from referee.reproducibility.code_metrics import code_metrics

def test_code_metrics_seed(tmp_path):
    p=tmp_path/'a.py';p.write_text('random.seed(7)\nprint(1)')
    assert code_metrics([p])['files'][0]['seed_mentions']>=1
