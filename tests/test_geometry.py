"""Seed relaxation and mesh topology: determinism, adjacency, and pathfinding."""

from __future__ import annotations

from doomgen.abstraction.layout import Area, AreaConfig, ConnectionType, LayoutGraph, Transform
from doomgen.geometry.mesh import VoronoiMesh
from doomgen.geometry.seeds import Seed, generate_relaxed_seeds

BOUNDS = (-512, -512, 512, 512)


def relaxed(num_seeds: int = 60, seed: int = 42) -> list[Seed]:
    return generate_relaxed_seeds(BOUNDS, num_seeds, seed=seed)


class TestSeeds:
    def test_seed_defaults_to_void(self):
        assert Seed(1.0, 2.0).area_id == "VOID"
        assert Seed(1.0, 2.0).is_boundary is False

    def test_relaxation_is_deterministic(self):
        first = [(s.x, s.y) for s in relaxed(seed=7)]
        second = [(s.x, s.y) for s in relaxed(seed=7)]

        assert first == second

    def test_different_seeds_differ(self):
        first = [(s.x, s.y) for s in relaxed(seed=7)]
        other = [(s.x, s.y) for s in relaxed(seed=8)]

        assert first != other

    def test_interior_seeds_stay_in_bounds(self):
        minx, miny, maxx, maxy = BOUNDS
        interior = [s for s in relaxed() if not s.is_boundary]

        assert len(interior) == 60
        assert all(minx <= s.x <= maxx and miny <= s.y <= maxy for s in interior)

    def test_boundary_ring_marks_edges(self):
        ring = [s for s in relaxed() if s.is_boundary]

        assert ring, "no boundary ring generated"
        assert all(s.area_id == "VOID" for s in ring)


def meshed(num_seeds: int = 60, seed: int = 42) -> VoronoiMesh:
    mesh = VoronoiMesh(relaxed(num_seeds, seed))
    mesh.build()
    return mesh


class TestMesh:
    def test_build_creates_cells_and_symmetric_adjacency(self):
        mesh = meshed()

        assert mesh.cells, "no cells built"
        for node, neighbors in mesh.adjacency.items():
            for other in neighbors:
                assert node in mesh.adjacency[other]

    def test_empty_seeds_build_without_error(self):
        mesh = VoronoiMesh([])
        mesh.build()

        assert mesh.cells == {}
        assert mesh.adjacency == {}

    def test_find_path_reaches_target_over_adjacent_cells(self):
        mesh = meshed()
        starts = list(mesh.cells)[:3]
        ends = list(mesh.cells)[-3:]

        path = mesh.find_path(starts, ends)

        assert path[0] in starts
        assert path[-1] in ends
        for current, nxt in zip(path, path[1:]):
            assert nxt in mesh.adjacency[current]

    def test_find_connection_matches_layout_graph(self):
        graph = LayoutGraph()
        id_a = graph.add_area(Area("a", Transform(0, 0), AreaConfig()))
        id_b = graph.add_area(Area("b", Transform(0, 0), AreaConfig()))
        graph.connect(id_a, id_b, ConnectionType.DOOR)
        mesh = VoronoiMesh(relaxed(), graph)
        mesh.build()

        connection = mesh._find_connection(id_a, id_b)

        assert connection is not None
        assert connection.type == ConnectionType.DOOR
        assert mesh._find_connection(id_a, "missing") is None

    def test_ridges_skip_void_and_same_area_pairs(self):
        mesh = meshed()
        for i in mesh.point_idx_to_area_id:
            mesh.point_idx_to_area_id[i] = "VOID"

        assert mesh.get_ridges_for_translation() == []
