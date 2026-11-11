"""Build the dandelion layout used in the README.

A round central puff with thin filament corridors radiating out to seed
tufts. The seed decides how many filaments exist, their angles and
lengths, which tufts sit high on steep stairs, and what enemies spawn
where.

Usage:
    python examples/dandelion.py
    python examples/dandelion.py --render assets/dandelion.png --strip assets/dandelion_seeds.png
"""

from __future__ import annotations

import argparse
import colorsys
import hashlib
import math
import random
from pathlib import Path

from shapely.geometry import Point

from doomgen import ProceduralMapBuilder

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
SEEDS = (7, 8, 9)

BOUNDS = (-2200, -2200, 2200, 2200)
NUM_SEEDS = 12000
ROSTER = ["ZOMBIEMAN", "SHOTGUN_GUY", "IMP", "DEMON"]
TUFT_FLOORS = ["CEIL5_1", "CEIL5_2", "FLAT5_4", "MFLR8_1", "FLOOR5_2", "GRASS2"]


def plan(seed: int):
    """Decide filament count, angles, lengths, tufts, and heights."""
    rng = random.Random(seed)
    count = rng.randint(8, 12)
    base = rng.uniform(0, 360)
    angles = sorted(
        (base + i * 360.0 / count + rng.uniform(-8, 8)) % 360 for i in range(count)
    )
    lengths = [rng.randint(1000, 1500) for _ in range(count)]
    radii = [rng.randint(120, 180) for _ in range(count)]
    high = set(rng.sample(range(count), count // 2))
    heights = [
        rng.choice([64, 80, 96]) if i in high else rng.choice([0, 8])
        for i in range(count)
    ]
    return rng, angles, lengths, radii, high, heights


def build_dandelion(seed: int = 7, num_seeds: int = NUM_SEEDS) -> ProceduralMapBuilder:
    """Build the dandelion layout without writing a WAD."""
    rng, angles, lengths, radii, high, heights = plan(seed)
    builder = ProceduralMapBuilder(bounds=BOUNDS, num_seeds=num_seeds, seed=seed)

    builder.add_area(
        "Puff",
        Point(0, 0).buffer(600, resolution=3),
        floor_height=0,
        ceiling_height=192,
        floor_texture="GRASS1",
        wall_texture="STONE2",
        light_level=255,
    )
    builder.add_area(
        "Core",
        Point(0, 0).buffer(250, resolution=3),
        floor_height=8,
        ceiling_height=192,
        floor_texture="FLAT14",
        wall_texture="MARBLE1",
        light_level=255,
        mode="overwrite",
    )
    builder.connect_adjacent("Puff", "Core")

    tufts = []
    for i, (angle, length, radius, height) in enumerate(
        zip(angles, lengths, radii, heights)
    ):
        name = f"Tuft {i + 1}"
        x = length * math.cos(math.radians(angle))
        y = length * math.sin(math.radians(angle))
        builder.add_area(
            name,
            Point(x, y).buffer(radius, resolution=2),
            floor_height=height,
            ceiling_height=192,
            floor_texture=rng.choice(TUFT_FLOORS),
            wall_texture="STARTAN3",
            light_level=255,
        )
        tufts.append(name)

    for i, tuft in enumerate(tufts):
        if i in high:
            builder.add_stairs("Puff", tuft, num_steps=6, width=3)
        else:
            builder.add_corridor(
                "Puff",
                tuft,
                width=3,
                floor_texture="FLOOR5_3",
                ceiling_height=192,
                wall_texture="BROWN96",
                light_level=220,
            )

    for thing_type, angle in (("PLAYER1_START", 0), ("PLAYER2_START", 180)):
        point = builder.get_random_point_in_area("Core")
        if point is not None:
            builder.add_thing(thing_type, point[0], point[1], angle=angle)
    pickup_point = builder.get_random_point_in_area("Core")
    if pickup_point is not None:
        builder.add_thing("SHOTGUN", pickup_point[0], pickup_point[1])

    for tuft in tufts:
        for _ in range(rng.randint(1, 4)):
            point = builder.get_random_point_in_area(tuft)
            if point is None:
                continue
            builder.add_thing(rng.choice(ROSTER), point[0], point[1])
    return builder


ENEMY_TYPES = {"ZOMBIEMAN", "SHOTGUN_GUY", "IMP", "DEMON"}
PICKUP_TYPES = {"SHOTGUN", "SUPER_SHOTGUN", "BOX_OF_SHELLS", "MEDIKIT"}

PALETTE = {
    "Puff": "#D8D8D2",
    "Core": "#E8C86A",
}
BACKGROUND = "#0B0E14"
LABEL_COLOR = "#E8EDF4"


def _thing_layers(builder: ProceduralMapBuilder):
    """Split placed things into starts, pickups, and enemies."""
    starts, pickups, enemies = [], [], []
    for thing in builder.things_to_add:
        point = (thing["x"], thing["y"])
        kind = str(thing["type"])
        if "START" in kind:
            starts.append(point)
        elif kind in PICKUP_TYPES:
            pickups.append(point)
        elif kind in ENEMY_TYPES:
            enemies.append(point)
        else:
            pickups.append(point)
    return starts, pickups, enemies


def _scatter_things(ax, builder, *, size_scale: float = 1.0) -> None:
    starts, pickups, enemies = _thing_layers(builder)
    if enemies:
        ax.scatter(
            [x for x, _ in enemies],
            [y for _, y in enemies],
            s=28 * size_scale,
            marker="x",
            color="#FF4D4D",
            linewidths=1.6,
            alpha=0.95,
            label="Enemy",
            zorder=5,
        )
    if pickups:
        ax.scatter(
            [x for x, _ in pickups],
            [y for _, y in pickups],
            s=48 * size_scale,
            marker="D",
            facecolor="#35E0C8",
            edgecolors="black",
            linewidths=0.8,
            alpha=0.95,
            label="Pickup",
            zorder=6,
        )
    if starts:
        ax.scatter(
            [x for x, _ in starts],
            [y for _, y in starts],
            s=170 * size_scale,
            marker="*",
            facecolor="white",
            edgecolors="black",
            linewidths=1.0,
            alpha=0.95,
            label="Start",
            zorder=7,
        )


def _render_helpers():
    try:
        import matplotlib.pyplot as plt
        from matplotlib.collections import PolyCollection
        from matplotlib.patheffects import withStroke
    except ImportError as exc:
        raise SystemExit(
            "Rendering needs matplotlib: pip install 'doomgen[viz]'"
        ) from exc
    return plt, PolyCollection, withStroke


def _area_name(builder: ProceduralMapBuilder, area_id: str) -> str:
    area = builder.graph.get_area(area_id)
    return area.name if area is not None else area_id


def _tuft_color(name: str, point_idx: int) -> tuple[float, float, float]:
    base = (237, 234, 224)
    digest = hashlib.sha256(f"{name}:{point_idx}".encode()).digest()
    delta = (digest[0] / 255 - 0.5) * 0.10
    red, green, blue = (c / 255 + delta for c in base)
    return (
        min(1.0, max(0.0, red)),
        min(1.0, max(0.0, green)),
        min(1.0, max(0.0, blue)),
    )


def _area_color(name: str, point_idx: int) -> tuple[float, float, float]:
    from matplotlib import colors as mcolors

    if name.startswith("Tuft"):
        return _tuft_color(name, point_idx)
    base = PALETTE.get(name, "#8A6F4D" if name.startswith("stairs") else "#5A6577")
    red, green, blue = mcolors.to_rgb(base)
    hue, _, saturation = colorsys.rgb_to_hls(red, green, blue)
    digest = hashlib.sha256(f"{name}:{point_idx}".encode()).digest()
    delta = (digest[0] / 255 - 0.5) * 0.08
    return colorsys.hls_to_rgb(
        (hue + delta) % 1.0, 0.52 + delta, max(0.0, saturation - 0.04)
    )


def _cell_polygons(builder: ProceduralMapBuilder):
    polygons = []
    colors = []
    for point_idx, polygon in builder.mesh.cells.items():
        area_id = builder.seeds[point_idx].area_id
        if area_id == "VOID" or polygon.is_empty:
            continue
        polygons.append(list(polygon.exterior.coords))
        colors.append(_area_color(_area_name(builder, area_id), point_idx))
    return polygons, colors


def _set_limits(ax, polygons) -> None:
    xs = [x for polygon in polygons for x, _ in polygon]
    ys = [y for polygon in polygons for _, y in polygon]
    margin = 40
    ax.set_xlim(min(xs) - margin, max(xs) + margin)
    ax.set_ylim(min(ys) - margin, max(ys) + margin)
    ax.set_aspect("equal")
    ax.axis("off")


def render_map(builder: ProceduralMapBuilder, output_path: str | Path) -> None:
    """Render one dandelion layout in the README style."""
    plt, PolyCollection, withStroke = _render_helpers()
    polygons, colors = _cell_polygons(builder)
    fig, ax = plt.subplots(figsize=(10, 10), facecolor=BACKGROUND)
    ax.set_facecolor(BACKGROUND)
    ax.add_collection(
        PolyCollection(
            polygons,
            facecolors=colors,
            edgecolors=BACKGROUND,
            linewidths=0.35,
            antialiased=True,
        )
    )

    positions: dict[str, list] = {}
    for seed in builder.seeds:
        if seed.area_id == "VOID":
            continue
        positions.setdefault(_area_name(builder, seed.area_id), []).append(
            (seed.x, seed.y)
        )
    for name, points in positions.items():
        if "corridor" in name or "stairs" in name:
            continue
        if name in ("Puff", "Core"):
            continue
        ax.text(
            sum(x for x, _ in points) / len(points),
            sum(y for _, y in points) / len(points),
            name.upper().replace("TUFT ", "T"),
            ha="center",
            va="center",
            color=LABEL_COLOR,
            fontsize=7.5 if name == "Core" else 6,
            fontweight="bold",
            alpha=0.85,
            path_effects=[withStroke(linewidth=2.5, foreground=BACKGROUND)],
        )

    _set_limits(ax, polygons)
    _scatter_things(ax, builder)
    legend = ax.legend(
        loc="lower right",
        fontsize=8,
        framealpha=0.85,
        facecolor="#161C26",
        edgecolor="#3A4356",
        labelcolor=LABEL_COLOR,
    )
    for text in legend.get_texts():
        text.set_path_effects([withStroke(linewidth=2, foreground=BACKGROUND)])
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    fig.savefig(
        output_path,
        dpi=220,
        facecolor=fig.get_facecolor(),
        bbox_inches="tight",
        pad_inches=0,
    )
    plt.close(fig)


def render_seed_strip(builders, output_path: str | Path) -> None:
    """Render the same layout at several seeds, one panel per seed."""
    plt, PolyCollection, _ = _render_helpers()
    fig, axes = plt.subplots(1, len(builders), figsize=(15, 5.2), facecolor=BACKGROUND)
    for ax, (seed, builder) in zip(axes, builders):
        polygons, colors = _cell_polygons(builder)
        ax.add_collection(
            PolyCollection(
                polygons,
                facecolors=colors,
                edgecolors=BACKGROUND,
                linewidths=0.3,
                antialiased=True,
            )
        )
        _set_limits(ax, polygons)
        _scatter_things(ax, builder, size_scale=0.8)
        ax.set_facecolor(BACKGROUND)
        ax.set_title(f"seed {seed}", color="#AEB7C6", fontsize=10, pad=6)

    fig.subplots_adjust(left=0, right=1, bottom=0, top=0.94, wspace=0.02)
    fig.savefig(
        output_path,
        dpi=200,
        facecolor=fig.get_facecolor(),
        bbox_inches="tight",
        pad_inches=0.05,
    )
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR / "dandelion.wad",
        help="WAD output path",
    )
    parser.add_argument("--render", type=Path, help="render a PNG of the layout")
    parser.add_argument("--strip", type=Path, help="render a seed-strip PNG")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    builder = build_dandelion(seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    builder.build(str(args.output))
    print(f"wrote {args.output}")

    if args.render:
        args.render.parent.mkdir(parents=True, exist_ok=True)
        render_map(builder, args.render)
        print(f"wrote {args.render}")

    if args.strip:
        builders = [(seed, build_dandelion(seed=seed)) for seed in SEEDS]
        for seed, strip_builder in builders:
            wad = OUTPUT_DIR / f"dandelion_seed_{seed}.wad"
            strip_builder.build(str(wad))
            print(f"wrote {wad}")
        args.strip.parent.mkdir(parents=True, exist_ok=True)
        render_seed_strip(builders, args.strip)
        print(f"wrote {args.strip}")


if __name__ == "__main__":
    main()
