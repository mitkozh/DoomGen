"""Pythonic ACS (Action Code Script) generation."""

from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Optional, Any
from enum import Enum, auto
from dataclasses import dataclass, field
from pathlib import Path


class ScriptType(Enum):
    """Types of ACS scripts."""
    OPEN = auto()       # Runs when map opens
    ENTER = auto()      # Runs when player enters
    RESPAWN = auto()    # Runs when player respawns
    DEATH = auto()      # Runs when player dies
    LIGHTNING = auto()  # Runs periodically for lightning
    UNLOADING = auto()  # Runs when map unloads
    DISCONNECT = auto() # Runs when player disconnects
    RETURN = auto()     # Runs when returning to map
    EVENT = auto()      # Custom event script
    KILL = auto()       # Runs when thing is killed
    REOPEN = auto()     # Runs when returning to hub
    VOID = auto()       # Callable script (void)


@dataclass
class ACSScript:
    """
    Represents a single ACS script.
    
    Attributes:
        number: Script number (1-999).
        script_type: Type of script trigger.
        body: C-style script body code.
        args: Script arguments (for ENTER scripts).
    """
    number: int
    script_type: ScriptType
    body: str
    args: list[str] = field(default_factory=list)
    
    def to_code(self) -> str:
        """Generate ACS code for this script."""
        type_str = {
            ScriptType.OPEN: "OPEN",
            ScriptType.ENTER: "ENTER",
            ScriptType.RESPAWN: "RESPAWN",
            ScriptType.DEATH: "DEATH",
            ScriptType.LIGHTNING: "LIGHTNING",
            ScriptType.UNLOADING: "UNLOADING",
            ScriptType.DISCONNECT: "DISCONNECT",
            ScriptType.RETURN: "RETURN",
            ScriptType.EVENT: "EVENT",
            ScriptType.KILL: "KILL",
            ScriptType.REOPEN: "REOPEN",
            ScriptType.VOID: "",
        }.get(self.script_type, "")
        
        # Build argument list
        if self.args:
            args_str = ", ".join(f"int {arg}" for arg in self.args)
            header = f"script {self.number} ({args_str})"
        elif type_str:
            header = f"script {self.number} {type_str}"
        else:
            header = f"script {self.number} (void)"
        
        return f"{header}\n{{\n{self._indent(self.body)}\n}}"
    
    def _indent(self, code: str, level: int = 1) -> str:
        """Indent code lines."""
        indent = "    " * level
        lines = code.strip().split("\n")
        return "\n".join(indent + line for line in lines)


class ACSBuilder:
    """
    Builder for ACS scripts.
    
    Provides a Pythonic interface for constructing ACS scripts
    that can be compiled and inserted into WAD files.
    
    Attributes:
        scripts: List of ACS scripts.
        includes: List of include directives.
        defines: Dictionary of #define macros.
        global_vars: List of global variables.
    """
    
    def __init__(self):
        """Initialize the ACS builder."""
        self.scripts: list[ACSScript] = []
        self.includes: list[str] = []
        self.defines: dict[str, Any] = {}
        self.global_vars: list[tuple[str, str, Any]] = []  # (name, type, initial)
        self._next_script_num = 1
    
    def add_include(self, filename: str) -> 'ACSBuilder':
        """
        Add an include directive.
        
        Args:
            filename: File to include (e.g., "zcommon.acs").
        
        Returns:
            Self for chaining.
        """
        self.includes.append(filename)
        return self
    
    def add_define(self, name: str, value: Any) -> 'ACSBuilder':
        """
        Add a #define macro.
        
        Args:
            name: Macro name.
            value: Macro value.
        
        Returns:
            Self for chaining.
        """
        self.defines[name] = value
        return self
    
    def add_global_var(
        self,
        name: str,
        var_type: str = "int",
        initial: Any = None
    ) -> 'ACSBuilder':
        """
        Add a global variable.
        
        Args:
            name: Variable name.
            var_type: Variable type ("int", "str", "bool").
            initial: Initial value.
        
        Returns:
            Self for chaining.
        """
        self.global_vars.append((name, var_type, initial))
        return self
    
    def add_script(
        self,
        script_type: ScriptType,
        body: str,
        number: Optional[int] = None,
        args: Optional[list[str]] = None
    ) -> int:
        """
        Add a new script.
        
        Args:
            script_type: Type of script trigger.
            body: Script body (C-style code).
            number: Script number (auto-assigned if None).
            args: Script arguments.
        
        Returns:
            The script number.
        """
        if number is None:
            number = self._next_script_num
            self._next_script_num += 1
        else:
            self._next_script_num = max(self._next_script_num, number + 1)
        
        script = ACSScript(
            number=number,
            script_type=script_type,
            body=body,
            args=args or []
        )
        
        self.scripts.append(script)
        return number
    
    def define_door_logic(
        self,
        tag: int,
        open_time: int = 35,  # Tics (35 = 1 second)
        close_time: int = 105,  # Tics until auto-close
        speed: int = 16
    ) -> int:
        """
        Create a door open/close script.
        
        Args:
            tag: Sector tag for the door.
            open_time: Time to stay open (in tics, 35 = 1 second).
            close_time: Time until auto-close.
            speed: Door movement speed.
        
        Returns:
            Script number.
        """
        body = f"""
Door_Open({tag}, {speed});
Delay({open_time});
Door_Close({tag}, {speed});
"""
        return self.add_script(ScriptType.OPEN, body.strip())
    
    def define_teleport_logic(
        self,
        source_tag: int,
        dest_tag: int
    ) -> int:
        """
        Create a teleporter script.
        
        Args:
            source_tag: Source sector tag.
            dest_tag: Destination thing tag.
        
        Returns:
            Script number.
        """
        body = f"""
Teleport({dest_tag}, 0, 0);
"""
        return self.add_script(ScriptType.ENTER, body.strip())
    
    def define_spawn_enemies(
        self,
        thing_type: int,
        spawn_tag: int,
        count: int = 1,
        delay: int = 35
    ) -> int:
        """
        Create an enemy spawn script.
        
        Args:
            thing_type: Doom thing type to spawn.
            spawn_tag: Thing tag for spawn location.
            count: Number to spawn.
            delay: Delay between spawns (tics).
        
        Returns:
            Script number.
        """
        body = f"""
for (int i = 0; i < {count}; i++)
{{
    SpawnSpot("{thing_type}", {spawn_tag});
    Delay({delay});
}}
"""
        return self.add_script(ScriptType.OPEN, body.strip())
    
    def define_message(
        self,
        message: str,
        script_type: ScriptType = ScriptType.ENTER
    ) -> int:
        """
        Create a message display script.
        
        Args:
            message: Message to display.
            script_type: When to trigger.
        
        Returns:
            Script number.
        """
        # Escape quotes in message
        escaped = message.replace('"', '\\"')
        body = f'Print(s:"{escaped}");'
        return self.add_script(script_type, body)
    
    def define_sector_light(
        self,
        tag: int,
        min_light: int = 64,
        max_light: int = 255,
        pulse_time: int = 35
    ) -> int:
        """
        Create a pulsing light effect.
        
        Args:
            tag: Sector tag.
            min_light: Minimum light level.
            max_light: Maximum light level.
            pulse_time: Pulse duration (tics).
        
        Returns:
            Script number.
        """
        body = f"""
while (true)
{{
    Light_Fade({tag}, {max_light}, {pulse_time});
    Delay({pulse_time});
    Light_Fade({tag}, {min_light}, {pulse_time});
    Delay({pulse_time});
}}
"""
        return self.add_script(ScriptType.OPEN, body.strip())
    
    def to_code(self) -> str:
        """
        Generate complete ACS source code.
        
        Returns:
            ACS source code as a string.
        """
        lines = []
        
        # Includes
        for inc in self.includes:
            lines.append(f'#include "{inc}"')
        
        if self.includes:
            lines.append("")
        
        # Defines
        for name, value in self.defines.items():
            lines.append(f"#define {name} {value}")
        
        if self.defines:
            lines.append("")
        
        # Map variables (script-level variables)
        for i, (name, var_type, initial) in enumerate(self.global_vars):
            if initial is not None:
                lines.append(f"{var_type} {name} = {initial};")
            else:
                lines.append(f"{var_type} {name};")
        
        if self.global_vars:
            lines.append("")
        
        # Scripts
        for script in self.scripts:
            lines.append(script.to_code())
            lines.append("")
        
        return "\n".join(lines)
    
    def compile(
        self,
        output_path: Optional[str | Path] = None,
        acc_path: str = "acc"
    ) -> Optional[bytes]:
        """
        Compile the ACS scripts to bytecode.
        
        Requires the ACC compiler to be installed and accessible.
        
        Args:
            output_path: Path for compiled output (temporary if None).
            acc_path: Path to ACC compiler executable.
        
        Returns:
            Compiled bytecode as bytes, or None if compilation fails.
        
        Raises:
            FileNotFoundError: If ACC compiler is not found.
            subprocess.CalledProcessError: If compilation fails.
        """
        source_code = self.to_code()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write source
            source_file = Path(tmpdir) / "script.acs"
            source_file.write_text(source_code)
            
            # Output file
            if output_path:
                obj_file = Path(output_path)
            else:
                obj_file = Path(tmpdir) / "script.o"
            
            # Compile
            try:
                result = subprocess.run(
                    [acc_path, str(source_file), str(obj_file)],
                    capture_output=True,
                    text=True,
                    check=True
                )
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"ACC compiler not found at '{acc_path}'. "
                    "Please install ACC and add it to your PATH."
                )
            
            # Read bytecode
            if obj_file.exists():
                return obj_file.read_bytes()
            
            return None
    
    def save_source(self, filepath: str | Path) -> None:
        """
        Save ACS source code to a file.
        
        Args:
            filepath: Output file path.
        """
        Path(filepath).write_text(self.to_code())
