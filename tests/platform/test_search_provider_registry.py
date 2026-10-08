from referee.providers.registry import ProviderRegistry

def test_federated_search_is_registered():
    assert 'federated' in ProviderRegistry().search_names()
