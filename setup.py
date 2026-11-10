"""Setuptools shim for building platform-specific DoomGen wheels."""

import os

from setuptools import setup
from setuptools.command.bdist_wheel import bdist_wheel


class PlatformWheel(bdist_wheel):
    """Force a py3-none-<platform> wheel when explicitly requested."""

    def get_tag(self) -> tuple[str, str, str]:
        if os.environ.get("DOOMGEN_PLATFORM_WHEEL") != "1":
            return super().get_tag()
        return "py3", "none", self.plat_name


setup(cmdclass={"bdist_wheel": PlatformWheel})
