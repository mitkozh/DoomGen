"""Smoke-test an installed DoomGen wheel: build a WAD with bundled ZDBSP."""

from __future__ import annotations

import tempfile
from pathlib import Path

from omg import WAD

from doomgen.builder import ProceduralMapBuilder
from doomgen.utils.paths import get_platform, resolve_compiler


def main() -> int:
    zdbsp = resolve_compiler("zdbsp")
    print(f"platform: {get_platform()}")
    print(f"zdbsp: {zdbsp}")

    with tempfile.TemporaryDirectory(prefix="doomgen-smoke-") as temp_dir:
        output = Path(temp_dir) / "smoke.wad"
        builder = ProceduralMapBuilder(
            bounds=(-512, -512, 512, 512),
            num_seeds=150,
            seed=42,
        )
        builder.add_area("hall", (0, 0, 256, 256))
        builder.add_thing("PLAYER1_START", 0, 0)
        builder.build(str(output))

        if not output.is_file():
            raise SystemExit("smoke WAD was not created")

        wad = WAD(str(output))
        lumps = list(wad.maps["MAP01"])
        if "NODES" not in lumps:
            raise SystemExit("smoke WAD has no NODES lump")

        print(f"created {output.name} with NODES")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
