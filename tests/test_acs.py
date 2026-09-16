"""ACS scripting: source rendering plus compilation through bundled ACC."""

from __future__ import annotations

import pytest

from doomgen.logic.acs_builder import (
    ACSBuilder,
    ACSScript,
    ACSVariable,
    ScriptType,
    VariableScope,
)
from doomgen.utils.paths import get_bundled_compiler


class TestRendering:
    def test_script_numbers_auto_increment(self):
        builder = ACSBuilder()

        assert builder.add_script(ScriptType.OPEN, "Delay(1);") == 1
        assert builder.add_script(ScriptType.ENTER, "Delay(1);") == 2

    def test_explicit_number_advances_counter(self):
        builder = ACSBuilder()
        builder.add_script(ScriptType.OPEN, "Delay(1);", number=10)

        assert builder.add_script(ScriptType.OPEN, "Delay(1);") == 11

    def test_script_header_uses_type_and_args(self):
        assert "OPEN" in ACSScript(1, ScriptType.OPEN, "Delay(1);").to_code()
        assert "(void)" in ACSScript(2, ScriptType.VOID, "Delay(1);").to_code()
        header = ACSScript(3, ScriptType.OPEN, "Delay(1);", args=["a"]).to_code()
        assert header.startswith("script 3 (int a)")

    def test_variables_render_per_scope(self):
        builder = (
            ACSBuilder()
            .add_map_var("counter", initial=0)
            .add_world_var("wave", 5)
            .add_global_var("score", 9)
        )
        code = builder.to_code()

        assert "int counter = 0;" in code
        assert "world int 5:wave;" in code
        assert "global int 9:score;" in code

    def test_world_var_without_index_fails(self):
        with pytest.raises(ValueError, match="must have an index"):
            ACSVariable("w", "int", VariableScope.WORLD).to_code()

    def test_global_var_without_index_fails(self):
        with pytest.raises(ValueError, match="must have an index"):
            ACSVariable("g", "int", VariableScope.GLOBAL).to_code()

    def test_helpers_emit_expected_calls(self):
        builder = ACSBuilder()
        builder.add_include("zcommon.acs").add_define("MAX", 3)
        builder.add_map_var("counter", initial=0)
        builder.define_door_logic(tag=1)
        builder.define_teleport_logic(source_tag=1, dest_tag=2)
        builder.define_spawn_enemies(thing_type=3001, spawn_tag=7)
        builder.define_message('Say "hi"')
        builder.define_sector_light(tag=4)
        code = builder.to_code()

        assert '#include "zcommon.acs"' in code
        assert "#define MAX 3" in code
        assert "Door_Open(1" in code
        assert "Teleport(2" in code
        assert 'SpawnSpot("3001", 7)' in code
        assert 'Print(s:"Say \\"hi\\"");' in code
        assert "Light_Fade(4" in code

    def test_save_source_roundtrips(self, tmp_path):
        builder = ACSBuilder()
        builder.add_script(ScriptType.OPEN, 'Print(s:"hi");')

        source = tmp_path / "script.acs"
        builder.save_source(source)

        assert source.read_text() == builder.to_code()


class TestCompilation:
    """End-to-end runs of the real bundled ACC (no subprocess mocks)."""

    def test_simple_script_compiles_to_bytecode(self, tmp_path):
        builder = ACSBuilder()
        builder.add_script(ScriptType.OPEN, 'Print(s:"Hello World");')

        bytecode = builder.compile(output_path=str(tmp_path / "hello.o"))

        assert bytecode is not None
        assert bytecode[:3] == b"ACS"

    def test_door_logic_compiles_with_zcommon(self, tmp_path):
        builder = ACSBuilder()
        builder.add_include("zcommon.acs")
        builder.add_map_var("counter", initial=0)
        builder.define_message("Door opened")
        builder.define_door_logic(tag=1)

        bytecode = builder.compile(output_path=str(tmp_path / "door.o"))

        assert bytecode is not None
        assert bytecode[:3] == b"ACS"

    def test_explicit_compiler_path_is_used(self, tmp_path):
        builder = ACSBuilder()
        builder.add_script(ScriptType.OPEN, 'Print(s:"explicit");')

        bytecode = builder.compile(
            output_path=str(tmp_path / "explicit.o"),
            acc_path=get_bundled_compiler("acc"),
        )

        assert bytecode is not None
        assert bytecode[:3] == b"ACS"

    def test_missing_compiler_raises_file_not_found(self, tmp_path):
        builder = ACSBuilder()
        builder.add_script(ScriptType.OPEN, 'Print(s:"Hello World");')

        with pytest.raises(FileNotFoundError):
            builder.compile(
                output_path=str(tmp_path / "missing.o"),
                acc_path="/nonexistent/path/to/acc",
            )

    def test_door_without_zcommon_reports_acc_error(self, tmp_path):
        builder = ACSBuilder()
        builder.define_door_logic(tag=1)

        with pytest.raises(RuntimeError, match="door_open"):
            builder.compile(output_path=str(tmp_path / "bad.o"))
