from referee.reproducibility.environment import detect_environment_files

def test_environment_detection(tmp_path):
    p=tmp_path/'requirements.txt';p.write_text('x')
    assert detect_environment_files([p])['reproducible_environment_declared']
