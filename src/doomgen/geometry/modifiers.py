"""Procedural shape modifiers: L-systems and fractal subdivision."""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
from numpy.random import Generator
from shapely.geometry import LineString, Polygon


# =============================================================================
# L-System Path Generation
# =============================================================================

# Default L-System grammars for different corridor styles
GRAMMARS = {
    # Simple zigzag - sharp 90° turns
    'zigzag': {
        'axiom': 'F',
        'rules': {'F': 'F+F-F-F+F'},
        'angle': 90,
    },
    # Koch-like curve - 60° turns
    'koch': {
        'axiom': 'F',
        'rules': {'F': 'F+F-F+F'},
        'angle': 60,
    },
    # Serpentine path - 45° turns (more winding)
    'serpentine': {
        'axiom': 'F',
        'rules': {'F': 'F+F-F'},
        'angle': 45,
    },
    # Branching (for exploration)
    'branching': {
        'axiom': 'X',
        'rules': {'X': 'F+[[X]-X]-F[-FX]+X', 'F': 'FF'},
        'angle': 25,
    },
    # Simple meander - 90° turns
    'meander': {
        'axiom': 'F',
        'rules': {'F': '+F-F-F+F'},
        'angle': 90,
    },
    # =========================================================================
    # New "organic" grammars - straighter with subtle variations
    # =========================================================================
    # Gentle curve - mostly straight with slight bends
    'gentle': {
        'axiom': 'F',
        'rules': {'F': 'FF+F-F'},
        'angle': 15,
    },
    # Slight wobble - nearly straight with tiny deviations
    'wobble': {
        'axiom': 'F',
        'rules': {'F': 'F+F-F-F+F'},
        'angle': 10,
    },
    # Organic - natural looking slight curves
    'organic': {
        'axiom': 'F',
        'rules': {'F': 'F-F+F'},
        'angle': 12,
    },
    # Straight with kinks - mostly straight with occasional turns
    'kinked': {
        'axiom': 'F',
        'rules': {'F': 'FFF+F-F'},
        'angle': 20,
    },
    # Wavy - gentle wave pattern
    'wavy': {
        'axiom': 'F',
        'rules': {'F': 'F+F-F-F+F'},
        'angle': 8,
    },
    # Direct - almost straight, minimal deviation
    'direct': {
        'axiom': 'F',
        'rules': {'F': 'FF-F+FF'},
        'angle': 5,
    },
}


class LSystemGenerator:
    """
    L-System path generator for procedural corridors.
    
    Commands:
        F: Move forward, drawing a line
        +: Turn left by angle
        -: Turn right by angle
        [: Push current state (position, angle)
        ]: Pop state
        
    Attributes:
        grammar: Dictionary with 'axiom', 'rules', 'angle' keys.
        rng: NumPy random generator for stochastic variations.
    
    Example:
        >>> gen = LSystemGenerator(grammar_name='serpentine', seed=42)
        >>> path = gen.generate_path((0, 0), (500, 0), iterations=2)
        >>> corridor = gen.generate_corridor((0, 0), (500, 0), width=64)
    """
    
    def __init__(
        self,
        grammar: Optional[dict] = None,
        grammar_name: Optional[str] = None,
        seed: Optional[int] = None,
        rng: Optional[Generator] = None
    ):
        """
        Args:
            grammar: Custom grammar dict with 'axiom', 'rules', 'angle'.
            grammar_name: Predefined grammar name (see GRAMMARS).
            seed: Random seed.
            rng: Existing NumPy generator.
        """
        if grammar is not None:
            self.grammar = grammar
        elif grammar_name is not None:
            if grammar_name not in GRAMMARS:
                raise ValueError(f"Unknown grammar: {grammar_name}. Available: {list(GRAMMARS.keys())}")
            self.grammar = GRAMMARS[grammar_name]
        else:
            self.grammar = GRAMMARS['zigzag']
        
        if rng is not None:
            self.rng = rng
        elif seed is not None:
            self.rng = np.random.default_rng(seed)
        else:
            self.rng = np.random.default_rng()
    
    def generate_string(self, iterations: int = 2) -> str:
        """
        Apply L-System rules to generate the instruction string.
        
        Args:
            iterations: Number of rule applications.
        
        Returns:
            The generated L-System string.
        """
        current = self.grammar['axiom']
        rules = self.grammar['rules']
        
        for _ in range(iterations):
            new_string = []
            for char in current:
                if char in rules:
                    new_string.append(rules[char])
                else:
                    new_string.append(char)
            current = ''.join(new_string)
        
        return current
    
    def interpret_string(
        self,
        lstring: str,
        start: tuple[float, float] = (0.0, 0.0),
        end: tuple[float, float] = (100.0, 0.0),
        angle_variation: float = 0.0
    ) -> list[tuple[float, float]]:
        """
        Interpret an L-System string as a path.
        
        The path is scaled and rotated to fit between start and end points.
        
        Args:
            lstring: The L-System string to interpret.
            start: Starting point of the path.
            end: Ending point of the path.
            angle_variation: Random variation added to turns (degrees).
        
        Returns:
            List of (x, y) points forming the path.
        """
        base_angle = self.grammar['angle']
        
        # First, generate path from origin pointing right
        points = [(0.0, 0.0)]
        state_stack = []
        
        x, y = 0.0, 0.0
        angle = 0.0  # Radians, 0 = pointing right
        step = 1.0  # Unit step, will be scaled later
        
        for char in lstring:
            if char == 'F':
                # Move forward
                x += step * math.cos(angle)
                y += step * math.sin(angle)
                points.append((x, y))
            elif char == '+':
                # Turn left
                variation = 0
                if angle_variation > 0:
                    variation = self.rng.uniform(-angle_variation, angle_variation)
                angle += math.radians(base_angle + variation)
            elif char == '-':
                # Turn right
                variation = 0
                if angle_variation > 0:
                    variation = self.rng.uniform(-angle_variation, angle_variation)
                angle -= math.radians(base_angle + variation)
            elif char == '[':
                # Push state
                state_stack.append((x, y, angle))
            elif char == ']':
                # Pop state
                if state_stack:
                    x, y, angle = state_stack.pop()
        
        if len(points) < 2:
            # Fallback to straight line
            return [start, end]
        
        # Transform path to fit between start and end
        points = self._fit_path_to_endpoints(points, start, end)
        
        return points
    
    def _fit_path_to_endpoints(
        self,
        points: list[tuple[float, float]],
        start: tuple[float, float],
        end: tuple[float, float]
    ) -> list[tuple[float, float]]:
        """Transform path to fit between two endpoints."""
        points = np.array(points)
        start = np.array(start)
        end = np.array(end)
        
        # Current start and end of path
        path_start = points[0]
        path_end = points[-1]
        
        # Translate to origin
        points = points - path_start
        path_end = path_end - path_start
        
        # Calculate required rotation
        target_vector = end - start
        target_angle = math.atan2(target_vector[1], target_vector[0])
        
        if np.linalg.norm(path_end) > 0:
            current_angle = math.atan2(path_end[1], path_end[0])
        else:
            current_angle = 0
        
        rotation = target_angle - current_angle
        
        # Apply rotation
        cos_r = math.cos(rotation)
        sin_r = math.sin(rotation)
        rotation_matrix = np.array([[cos_r, -sin_r], [sin_r, cos_r]])
        points = points @ rotation_matrix.T
        
        # Calculate required scale
        target_length = np.linalg.norm(target_vector)
        current_length = np.linalg.norm(points[-1])
        
        if current_length > 0:
            scale = target_length / current_length
        else:
            scale = 1.0
        
        points = points * scale
        
        # Translate to start position
        points = points + start
        
        return [tuple(p) for p in points]
    
    def generate_path(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        iterations: int = 2,
        angle_variation: float = 0.0,
        max_deviation: Optional[float] = None
    ) -> list[tuple[float, float]]:
        """
        Generate a complete path between two points.
        
        This is the main entry point for corridor path generation.
        
        Args:
            start: Starting point.
            end: Ending point.
            iterations: L-System iterations (complexity).
            angle_variation: Random variation in turn angles.
            max_deviation: Maximum perpendicular distance from the direct line
                          as a fraction of the total distance (0.0-1.0).
                          E.g., 0.3 means path can deviate up to 30% of the
                          start-to-end distance. None = no constraint.
        
        Returns:
            List of points forming the path.
        """
        # If max_deviation is set, use the forward-only path generation
        # which guarantees no backtracking
        if max_deviation is not None:
            return self._generate_forward_path(start, end, iterations, max_deviation)
        
        # Original L-system path (may have backtracking)
        lstring = self.generate_string(iterations)
        return self.interpret_string(lstring, start, end, angle_variation)
    
    def _generate_forward_path(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        iterations: int,
        max_deviation: float
    ) -> list[tuple[float, float]]:
        """
        Generate a path that ONLY moves forward, with perpendicular variation.
        
        This guarantees no backtracking by:
        1. Dividing the path into evenly-spaced segments along the direct line
        2. Only varying the perpendicular offset at each point
        3. Using smooth transitions between offsets
        
        Args:
            start: Starting point.
            end: Ending point.
            iterations: Controls number of segments (more = more detail).
            max_deviation: Maximum perpendicular deviation as fraction of distance.
        
        Returns:
            List of points forming a forward-only path.
        """
        start = np.array(start)
        end = np.array(end)
        
        direction = end - start
        total_dist = np.linalg.norm(direction)
        
        if total_dist < 1:
            return [tuple(start), tuple(end)]
        
        direction_norm = direction / total_dist
        perp = np.array([-direction_norm[1], direction_norm[0]])
        
        max_perp_dist = total_dist * max_deviation
        
        # Number of segments based on iterations and distance
        # More iterations = more segments = more detail
        base_segments = 3 + iterations * 2
        num_segments = min(base_segments, max(3, int(total_dist / 64)))
        
        # Generate random perpendicular offsets using the L-system grammar's angle
        # to influence the "waviness" 
        base_angle = self.grammar['angle']
        waviness = base_angle / 90.0  # 0-1 scale based on grammar angle
        
        points = [tuple(start)]
        
        # Generate offsets for intermediate points
        offsets = []
        for i in range(1, num_segments):
            # Random offset scaled by waviness and max_deviation
            offset = self.rng.uniform(-1, 1) * max_perp_dist * waviness
            offsets.append(offset)
        
        # Smooth the offsets to avoid sharp zigzags
        if len(offsets) > 2:
            smoothed = []
            for i in range(len(offsets)):
                if i == 0:
                    smoothed.append((offsets[0] + offsets[1]) / 2)
                elif i == len(offsets) - 1:
                    smoothed.append((offsets[-1] + offsets[-2]) / 2)
                else:
                    smoothed.append((offsets[i-1] + offsets[i] + offsets[i+1]) / 3)
            offsets = smoothed
        
        # Build path with forward progress guaranteed
        for i in range(1, num_segments):
            t = i / num_segments
            # Point along the direct line
            base_point = start + direction * t
            # Add perpendicular offset
            offset = offsets[i - 1] if i - 1 < len(offsets) else 0
            point = base_point + perp * offset
            points.append(tuple(point))
        
        points.append(tuple(end))
        
        return points
    
    def _constrain_path_deviation(
        self,
        points: list[tuple[float, float]],
        start: tuple[float, float],
        end: tuple[float, float],
        max_deviation: float
    ) -> list[tuple[float, float]]:
        """
        Constrain path points to stay within max_deviation of the direct line,
        and ensure monotonic forward progress (no backtracking).
        
        Args:
            points: The path points.
            start: Start point.
            end: End point.
            max_deviation: Maximum deviation as fraction of total distance.
        
        Returns:
            Constrained path points.
        """
        start = np.array(start)
        end = np.array(end)
        
        # Direction vector and perpendicular
        direction = end - start
        total_dist = np.linalg.norm(direction)
        
        if total_dist < 1:
            return points
        
        direction_norm = direction / total_dist
        perp = np.array([-direction_norm[1], direction_norm[0]])
        
        max_perp_dist = total_dist * max_deviation
        
        constrained = [points[0]]  # Keep start point
        last_progress = 0.0  # Track forward progress
        
        for i in range(1, len(points) - 1):
            p = np.array(points[i])
            
            # Vector from start to point
            to_point = p - start
            
            # Project onto direction (progress along path)
            progress = np.dot(to_point, direction_norm)
            
            # Perpendicular distance from line
            perp_dist = np.dot(to_point, perp)
            
            # Clamp perpendicular distance
            if abs(perp_dist) > max_perp_dist:
                perp_dist = np.sign(perp_dist) * max_perp_dist
            
            # ENFORCE MONOTONIC FORWARD PROGRESS - no backtracking allowed
            # Each point must be at least as far forward as the previous
            if progress < last_progress:
                progress = last_progress + 1.0  # Small forward step
            
            # Clamp to reasonable range
            progress = np.clip(progress, 0, total_dist)
            last_progress = progress
            
            # Reconstruct point
            new_point = start + direction_norm * progress + perp * perp_dist
            constrained.append(tuple(new_point))
        
        constrained.append(points[-1])  # Keep end point
        
        return constrained
    
    def generate_corridor(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        width: float,
        iterations: int = 2,
        max_deviation: Optional[float] = None
    ) -> Polygon:
        """
        Generate a corridor polygon following an L-System path.
        
        Args:
            start: Starting point.
            end: Ending point.
            width: Corridor width.
            iterations: L-System iterations.
            max_deviation: Maximum perpendicular deviation from direct line
                          as a fraction of total distance (0.0-1.0).
                          E.g., 0.2 means corridor can deviate up to 20%.
        
        Returns:
            Polygon representing the corridor.
        """
        path = self.generate_path(start, end, iterations, max_deviation=max_deviation)
        
        if len(path) < 2:
            # Fallback: straight corridor
            path = [start, end]
        
        line = LineString(path)
        corridor = line.buffer(width / 2, cap_style='round', join_style='round')
        
        return corridor


def create_lsystem_corridor(
    start: tuple[float, float],
    end: tuple[float, float],
    width: float,
    grammar_name: str = 'serpentine',
    iterations: int = 2,
    seed: Optional[int] = None,
    max_deviation: Optional[float] = None
) -> Polygon:
    """
    Convenience function to create an L-System corridor.
    
    Args:
        start: Starting point.
        end: Ending point.
        width: Corridor width.
        grammar_name: L-system grammar to use.
        iterations: L-System iterations (complexity).
        seed: Random seed.
        max_deviation: Maximum perpendicular deviation from direct line
                      as a fraction of total distance (0.0-1.0).
                      E.g., 0.2 = corridor can deviate up to 20% of the distance.
    """
    generator = LSystemGenerator(grammar_name=grammar_name, seed=seed)
    return generator.generate_corridor(start, end, width, iterations, max_deviation=max_deviation)


# =============================================================================
# Fractal Edge Subdivision
# =============================================================================

def recursive_subdivision(
    polygon: Polygon,
    iterations: int = 2,
    roughness: float = 0.3,
    rng: Optional[Generator] = None,
    seed: Optional[int] = None
) -> Polygon:
    """
    Apply fractal subdivision to polygon edges for organic shapes.
    
    Args:
        polygon: Input polygon.
        iterations: Subdivision iterations (each doubles vertices).
        roughness: Displacement magnitude (0.0-1.0).
        rng: NumPy random generator.
        seed: Random seed.
    
    Returns:
        New polygon with subdivided edges.
    
    Example:
        >>> from shapely.geometry import Polygon
        >>> square = Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])
        >>> rough_square = recursive_subdivision(square, iterations=3, roughness=0.2)
    """
    if iterations <= 0:
        return polygon
    
    if roughness < 0 or roughness > 1:
        raise ValueError(f"Roughness must be between 0 and 1, got {roughness}")
    
    # Set up random generator
    if rng is None:
        rng = np.random.default_rng(seed)
    
    # Get coordinates (excluding closing duplicate)
    coords = list(polygon.exterior.coords[:-1])
    
    for iteration in range(iterations):
        new_coords = []
        # Roughness decreases with each iteration for natural look
        current_roughness = roughness * (0.5 ** iteration)
        
        for i in range(len(coords)):
            p1 = np.array(coords[i])
            p2 = np.array(coords[(i + 1) % len(coords)])
            
            # Add the current point
            new_coords.append(tuple(p1))
            
            # Calculate midpoint
            midpoint = (p1 + p2) / 2
            
            # Calculate edge vector and perpendicular
            edge = p2 - p1
            edge_length = np.linalg.norm(edge)
            
            if edge_length < 1:  # Skip very short edges
                continue
            
            # Perpendicular vector (normalized)
            perp = np.array([-edge[1], edge[0]])
            perp = perp / np.linalg.norm(perp)
            
            # Random displacement
            displacement = rng.uniform(-1, 1) * current_roughness * edge_length
            
            # New point
            new_point = midpoint + perp * displacement
            new_coords.append(tuple(new_point))
        
        coords = new_coords
    
    # Create new polygon
    result = Polygon(coords)
    
    # Validate and fix if needed
    if not result.is_valid:
        result = result.buffer(0)  # Fix self-intersections
        if result.geom_type == 'MultiPolygon':
            result = max(result.geoms, key=lambda p: p.area)
    
    return result


def subdivide_edge(
    p1: tuple[float, float],
    p2: tuple[float, float],
    segments: int,
    roughness: float,
    rng: Generator
) -> list[tuple[float, float]]:
    """
    Subdivide a single edge into multiple segments with displacement.
    
    Args:
        p1: Start point of edge.
        p2: End point of edge.
        segments: Number of segments to create.
        roughness: Maximum displacement as fraction of edge length.
        rng: NumPy random generator.
    
    Returns:
        List of points along the subdivided edge (excluding endpoints).
    """
    p1 = np.array(p1)
    p2 = np.array(p2)
    
    edge = p2 - p1
    edge_length = np.linalg.norm(edge)
    
    if edge_length < 1:
        return []
    
    # Perpendicular vector
    perp = np.array([-edge[1], edge[0]])
    perp = perp / np.linalg.norm(perp)
    
    points = []
    for i in range(1, segments):
        t = i / segments
        point = p1 + edge * t
        
        # Displacement varies by position (less at edges)
        position_factor = 4 * t * (1 - t)  # Peaks at center
        displacement = rng.uniform(-1, 1) * roughness * edge_length * position_factor
        
        point = point + perp * displacement
        points.append(tuple(point))
    
    return points


def add_noise_to_polygon(
    polygon: Polygon,
    noise_scale: float = 10.0,
    rng: Optional[Generator] = None,
    seed: Optional[int] = None
) -> Polygon:
    """
    Add random noise to each vertex of a polygon.
    
    Unlike recursive_subdivision, this doesn't add new vertices,
    just displaces existing ones.
    
    Args:
        polygon: Input polygon.
        noise_scale: Maximum displacement in map units.
        rng: NumPy random generator.
        seed: Random seed (used if rng not provided).
    
    Returns:
        Polygon with noisy vertices.
    """
    if rng is None:
        rng = np.random.default_rng(seed)
    
    coords = list(polygon.exterior.coords[:-1])
    
    new_coords = []
    for x, y in coords:
        dx = rng.uniform(-noise_scale, noise_scale)
        dy = rng.uniform(-noise_scale, noise_scale)
        new_coords.append((x + dx, y + dy))
    
    result = Polygon(new_coords)
    
    if not result.is_valid:
        result = result.buffer(0)
        if result.geom_type == 'MultiPolygon':
            result = max(result.geoms, key=lambda p: p.area)
    
    return result
