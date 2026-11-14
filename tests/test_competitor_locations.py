"""Offline regression tests for geographic competitor identity and chain locations."""
from backend import local_competition as local


class _Reply:
    def __init__(self, elements):
        self.elements = elements

    def raise_for_status(self):
        return None

    def json(self):
        return {"elements": self.elements}


class _Overpass:
    def __init__(self, elements):
        self.elements = elements

    def post(self, *_args, **_kwargs):
        return _Reply(self.elements)


def _pizza(osm_id, lat, lon):
    return {
        "type": "node", "id": osm_id, "lat": lat, "lon": lon,
        "tags": {"name": "Pizza Planet", "cuisine": "pizza", "website": "https://pizzaplanet.example"},
    }


def test_osm_preserves_distinct_franchise_locations_sharing_a_domain():
    a = _pizza(101, 39.5, -76.3)
    b = _pizza(102, 39.51, -76.31)
    rows, warning = local.osm_competitors(_Overpass([a, a, b]), 39.5, -76.3, {"key": "pizza"}, "other.example", 15)
    assert warning is None
    assert {row["osm_id"] for row in rows} == {101, 102}
    assert len(rows) == 2
    assert all(row["website"] == "https://pizzaplanet.example" for row in rows)


def test_geoapify_reconciliation_keeps_two_branches_but_matches_same_location(monkeypatch):
    locations = [
        {"name": "Pizza Planet", "website": "https://pizzaplanet.example",
         "provider_id": "osm-node-101", "lat": 39.5, "lon": -76.3},
        {"name": "Pizza Planet", "website": "https://pizzaplanet.example",
         "provider_id": "osm-node-102", "lat": 39.51, "lon": -76.31},
    ]
    osm = [
        {"name": "Pizza Planet", "website": "https://pizzaplanet.example",
         "distance_miles": 0.0, "lat": 39.50002, "lon": -76.30002,
         "osm_type": "node", "osm_id": 101},
        {"name": "Pizza Planet", "website": "https://pizzaplanet.example",
         "distance_miles": 0.9, "lat": 39.51002, "lon": -76.31002,
         "osm_type": "node", "osm_id": 102},
    ]
    monkeypatch.setattr(local, "geoapify_places", lambda *_args: (locations, None))
    monkeypatch.setattr(local, "osm_competitors", lambda *_args: (osm, None))
    rows, warning, coverage = local.discover_competitors(object(), 39.5, -76.3, {"key": "pizza"}, "target.example", 15)
    assert warning is None
    assert len(rows) == 2
    assert all(row["source_providers"] == ["Geoapify", "Overpass"] for row in rows)
    assert "OpenStreetMap-derived" in coverage


def test_equal_distance_from_target_is_not_same_physical_location(monkeypatch):
    geo = [{"name": "Pizza Planet", "website": "https://pizzaplanet.example",
            "provider_id": "osm-node-301", "lat": 39.51, "lon": -76.3}]
    osm = [{"name": "Pizza Planet", "website": "https://pizzaplanet.example",
            "distance_miles": 0.7, "lat": 39.49, "lon": -76.3,
            "osm_type": "node", "osm_id": 302}]
    monkeypatch.setattr(local, "geoapify_places", lambda *_args: (geo, None))
    monkeypatch.setattr(local, "osm_competitors", lambda *_args: (osm, None))
    rows, _, _ = local.discover_competitors(object(), 39.5, -76.3, {"key": "pizza"}, "target.example", 15)
    assert len(rows) == 2
    assert all(len(row["source_providers"]) == 1 for row in rows)
