from referee.plugins import PluginRegistry

def test_plugin_registry_groups_declared():
    assert 'referee.llm' in PluginRegistry.GROUPS
