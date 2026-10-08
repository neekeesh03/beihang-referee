from referee.security import scan_secrets, redact_secrets

def test_secret_redaction():
    t='api_key = supersecretvalue123'
    assert scan_secrets(t)
    assert 'supersecretvalue123' not in redact_secrets(t)
