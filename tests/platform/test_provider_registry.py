from referee.providers.registry import ProviderRegistry

def test_provider_registry_has_scripted():
    r=ProviderRegistry(); assert 'scripted' in r.llm_names() and 'scripted' in r.search_names()
