"""
Geometry Utilities
Common geometric calculations for the vTAXI system.
"""

import math
from typing import Tuple

def calculate_distance(point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
    """
    Calculate the distance between two points.
    
    Args:
        point1: First point (x, y)
        point2: Second point (x, y)
        
    Returns:
        Distance in meters
    """
    x1, y1 = point1
    x2, y2 = point2
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

def calculate_bearing(point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
    """
    Calculate the bearing from point1 to point2.
    
    Args:
        point1: Starting point (x, y)
        point2: Target point (x, y)
        
    Returns:
        Bearing in degrees (0-360)
    """
    x1, y1 = point1
    x2, y2 = point2
    
    dx = x2 - x1
    dy = y2 - y1
    
    bearing = math.degrees(math.atan2(dy, dx))
    return bearing % 360 