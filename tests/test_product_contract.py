"""Release-facing contract checks for beta product capabilities."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_premium_interactive_features_exist():
    script=(ROOT/'frontend'/'local-premium.js').read_text()
    for marker in ('Business explorer','Evidence-linked feature comparison',
                   'Prioritized opportunity playbooks','Measure success:',
                   'growthlens:report'):
        assert marker in script
    assert 'Financial what-if simulator' not in script
    assert 'glVisits' not in script

def test_only_one_local_panel_script_and_premium_script():
    html=(ROOT/'frontend'/'index.html').read_text()
    assert html.count('src="/local-competition.js"') == 1
    assert html.count('src="/local-premium.js"') == 1
    assert html.find('src="/local-premium.js"') > html.find('src="/local-competition.js"')

def test_no_api_key_exposed_in_client():
    script=(ROOT/'frontend'/'local-premium.js').read_text()
    assert 'GEOAPIFY_API_KEY' not in script
    assert 'api.geoapify.com' not in script

def test_geoapify_is_optional():
    from backend.providers import geoapify_places
    assert callable(geoapify_places)
