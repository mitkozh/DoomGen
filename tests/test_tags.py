"""Tag registry: unique sector tags for doors, lifts, and script targets."""

from __future__ import annotations

import pytest

from doomgen.doom.tags import TagRegistry


class TestTagRegistry:
    def test_allocates_sequentially_from_one(self):
        registry = TagRegistry()

        assert (registry.allocate(), registry.allocate()) == (1, 2)

    def test_custom_start_tag(self):
        assert TagRegistry(start_tag=100).allocate() == 100

    def test_named_tags_resolve(self):
        registry = TagRegistry()
        tag = registry.allocate(name="door1")

        assert registry.get("door1") == tag

    def test_unknown_name_raises(self):
        with pytest.raises(KeyError, match="door"):
            TagRegistry().get("door")

    def test_reserve_claims_specific_tag(self):
        registry = TagRegistry()
        registry.reserve(10, name="lift")

        assert registry.is_used(10)
        assert registry.get("lift") == 10
        assert registry.allocate() == 11

    def test_reserve_used_tag_raises(self):
        registry = TagRegistry()
        registry.allocate()

        with pytest.raises(ValueError, match="already in use"):
            registry.reserve(1)

    def test_get_or_allocate_is_idempotent(self):
        registry = TagRegistry()

        assert registry.get_or_allocate("door") == registry.get_or_allocate("door")

    def test_named_mapping_returns_copy(self):
        registry = TagRegistry()
        registry.allocate(name="door")
        mapping = registry.list_named_tags()
        mapping["door"] = 999

        assert registry.get("door") != 999

    def test_reset_restarts_sequence(self):
        registry = TagRegistry()
        registry.allocate()
        registry.reset()

        assert registry.allocate() == 1
        assert not registry.is_used(2)
