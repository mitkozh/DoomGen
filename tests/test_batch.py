"""Batch generation: scenario configs and cartesian expansion."""

from __future__ import annotations

from typing import Any

import pytest

from doomgen.batch import BatchGenerator, Scenario


class ToyScenario(Scenario):
    def get_default_config(self) -> dict[str, Any]:
        return {"size": 1, "seed": 0}

    def validate_config(self) -> None:
        if self.config["size"] < 1:
            raise ValueError("size must be positive")

    def generate(self, output_path: str) -> None:
        with open(output_path, "w") as f:
            f.write(f"{self.name}:{self.config['size']}:{self.config['seed']}")


class TestScenario:
    def test_defaults_apply_without_overrides(self):
        scenario = ToyScenario()

        assert scenario.name == "scenario"
        assert scenario.get_param("size") == 1
        assert scenario.get_param("missing") is None

    def test_config_overrides_merge(self):
        scenario = ToyScenario({"seed": 7}, name="run")

        assert (scenario.name, scenario.config["seed"]) == ("run", 7)
        assert scenario.config["size"] == 1

    def test_invalid_config_rejected_at_construction(self):
        with pytest.raises(ValueError, match="positive"):
            ToyScenario({"size": 0})

    def test_generate_writes_output(self, tmp_path):
        out = tmp_path / "toy.txt"
        ToyScenario({"size": 2, "seed": 3}, name="toy").generate(str(out))

        assert out.read_text() == "toy:2:3"


class TestBatchGenerator:
    GRID = {"size": [1, 2], "seed": [10, 20, 30]}

    def test_count_matches_cartesian_product(self):
        assert BatchGenerator(ToyScenario, self.GRID).count_combinations() == 6

    def test_configs_cover_every_combination(self):
        configs = list(BatchGenerator(ToyScenario, self.GRID).generate_configs())

        assert configs == [
            {"size": 1, "seed": 10},
            {"size": 1, "seed": 20},
            {"size": 1, "seed": 30},
            {"size": 2, "seed": 10},
            {"size": 2, "seed": 20},
            {"size": 2, "seed": 30},
        ]

    def test_scenarios_numbered_and_initialized(self):
        scenarios = list(BatchGenerator(ToyScenario, self.GRID).generate_scenarios("run"))

        assert [s.name for s in scenarios] == [f"run_{i}" for i in range(6)]
        assert all(isinstance(s, ToyScenario) for s in scenarios)
        assert scenarios[0].config == {"size": 1, "seed": 10}

    def test_empty_grid_yields_single_default(self):
        scenarios = list(BatchGenerator(ToyScenario, {}).generate_scenarios())

        assert len(scenarios) == 1
        assert scenarios[0].config == {"size": 1, "seed": 0}
