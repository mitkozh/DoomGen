"""Layout graph: the area/connection model the builder translates to sectors."""

from __future__ import annotations

from doomgen.abstraction.layout import (
    Area,
    AreaConfig,
    Connection,
    ConnectionType,
    LayoutGraph,
    Transform,
)


class TestLayoutGraph:
    def test_add_and_get_area_roundtrip(self):
        graph = LayoutGraph()
        area_id = graph.add_area(Area("hall", Transform(1, 2), AreaConfig()))

        assert graph.get_area(area_id).name == "hall"
        assert graph.get_area("missing") is None

    def test_connect_records_type_and_properties(self):
        graph = LayoutGraph()
        id_a = graph.add_area(Area("a", Transform(0, 0)))
        id_b = graph.add_area(Area("b", Transform(0, 0)))

        graph.connect(id_a, id_b, ConnectionType.DOOR, tag=5)

        (connection,) = graph.connections
        assert (connection.area_a_id, connection.area_b_id) == (id_a, id_b)
        assert connection.type == ConnectionType.DOOR
        assert connection.properties["tag"] == 5

    def test_area_tags(self):
        area = Area("hall", Transform(0, 0))
        area.add_tag("spawn")

        assert "spawn" in area.tags


class TestDomainTypes:
    def test_area_config_defaults_match_doom_defaults(self):
        config = AreaConfig()

        assert (config.floor_height, config.ceiling_height) == (0, 128)
        assert config.light_level == 160
        assert config.linedef_args == []
        assert config.properties == {}

    def test_connection_types_cover_open_solid_door_window(self):
        assert {t.value for t in ConnectionType} == {"open", "solid", "door", "window"}

    def test_connection_defaults_to_open(self):
        assert Connection("a", "b").type == ConnectionType.OPEN
