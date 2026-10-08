from referee.ingestion import PackageInspector

def test_package_inspector_hashes_file(tmp_path):
    p=tmp_path/'paper.md';p.write_text('paper')
    a=PackageInspector().inspect([p]).to_dict()
    assert a['files'][0]['sha256'] and a['roles']['manuscript']
