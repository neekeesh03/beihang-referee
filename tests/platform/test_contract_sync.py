import json
from pathlib import Path
from referee.contracts import concern_json_schema

def test_major_comment_schema_is_generated_from_canonical_contract():
    root=Path(__file__).resolve().parents[2]
    disk=json.loads((root/'schemas'/'major_comment.schema.json').read_text())
    assert disk==concern_json_schema()
