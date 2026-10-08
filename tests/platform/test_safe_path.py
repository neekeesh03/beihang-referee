import pytest
from referee.security.paths import safe_output_path

def test_safe_output_rejects_escape(tmp_path):
    with pytest.raises(ValueError): safe_output_path(tmp_path,'../x')
