"""Seed generation for Voronoi-first map generation."""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional
import numpy as np
import math
from scipy.spatial import Voronoi

@dataclass
class Seed:
    """A single Voronoi seed."""
    x: float
    y: float
    area_id: str = "VOID"
    is_boundary: bool = False

def generate_relaxed_seeds(
    bounds: Tuple[float, float, float, float],
    num_seeds: int,
    iterations: int = 5,
    seed: Optional[int] = None
) -> List[Seed]:
    """Generate seeds using Lloyd relaxation plus a boundary ring."""
    rng = np.random.default_rng(seed)
    minx, miny, maxx, maxy = bounds
    width = maxx - minx
    height = maxy - miny

    points = rng.uniform(
        low=[minx, miny],
        high=[maxx, maxy],
        size=(num_seeds, 2)
    )

    for _ in range(iterations):
        dummy_points = np.array([
            [minx - width, miny - height],
            [minx - width, maxy + height],
            [maxx + width, miny - height],
            [maxx + width, maxy + height],
            [minx - width, (miny + maxy)/2],
            [maxx + width, (miny + maxy)/2],
            [(minx + maxx)/2, miny - height],
            [(minx + maxx)/2, maxy + height],
        ])

        all_points = np.vstack([points, dummy_points])
        vor = Voronoi(all_points)

        vert_lists: list[list[int] | None] = []
        max_len = 0
        for region_idx in vor.point_region[: len(points)]:
            region = vor.regions[region_idx] if region_idx != -1 else []
            if not region or -1 in region:
                vert_lists.append(None)
            else:
                vert_lists.append(region)
                max_len = max(max_len, len(region))

        if max_len:
            mat = np.full((len(points), max_len), -1)
            for i, verts in enumerate(vert_lists):
                if verts:
                    mat[i, : len(verts)] = verts
            flat = mat.ravel()
            hit = flat >= 0
            owners = np.repeat(np.arange(len(points)), max_len)[hit]
            sums = np.zeros((len(points), 2))
            np.add.at(sums, owners, vor.vertices[flat[hit]])
            counts = np.bincount(owners, minlength=len(points))
            has = counts > 0
            centroids = points.copy()
            centroids[has] = sums[has] / counts[has, None]
            points = np.clip(centroids, [minx, miny], [maxx, maxy])

    seeds = [Seed(p[0], p[1]) for p in points]

    area = width * height
    if num_seeds > 0:
        avg_area_per_seed = area / num_seeds
        avg_spacing = math.sqrt(avg_area_per_seed)
    else:
        avg_spacing = 32.0

    step = avg_spacing
    margin = avg_spacing * 1.5

    bx_min = minx - margin
    bx_max = maxx + margin
    by_min = miny - margin
    by_max = maxy + margin

    for x in np.arange(bx_min, bx_max + step, step):
        seeds.append(Seed(x, by_min, is_boundary=True))
        seeds.append(Seed(x, by_max, is_boundary=True))

    for y in np.arange(by_min + step, by_max, step):
        seeds.append(Seed(bx_min, y, is_boundary=True))
        seeds.append(Seed(bx_max, y, is_boundary=True))

    return seeds
