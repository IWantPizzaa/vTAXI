from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

class AircraftSize(Enum):
    """Aircraft size categories according to ICAO"""
    LIGHT = auto()          # < 7,000 kg
    MEDIUM = auto()         # 7,000 kg - 136,000 kg
    HEAVY = auto()          # > 136,000 kg
    SUPER = auto()          # A380, AN225

@dataclass
class AircraftType:
    """Physical characteristics of an aircraft type"""
    size: AircraftSize
    max_taxi_speed: float           # Maximum taxi speed in knots
    max_acceleration: float         # Maximum acceleration in m/s²
    max_deceleration: float        # Maximum deceleration in m/s²

class AircraftPhysics:
    """Handles simplified aircraft ground movement physics"""
    
    def __init__(self, aircraft_type: AircraftType):
        self.aircraft_type = aircraft_type
        self.current_speed = 0.0    # Current speed in knots
        self.current_heading = 0.0   # Current heading in degrees
        
        # Convert knots to m/s for internal calculations
        self._max_speed_ms = self.aircraft_type.max_taxi_speed * 0.514444
        
        # Safety margin
        self._speed_safety_margin = 0.9  # 90% of max speed
    
    def calculate_acceleration(self, desired_speed: float, distance_to_stop: Optional[float] = None) -> float:
        """
        Calculate safe acceleration/deceleration based on current state and constraints
        
        Args:
            desired_speed: Target speed in knots
            distance_to_stop: Distance to next stop point in meters (if applicable)
            
        Returns:
            Safe acceleration/deceleration rate in m/s²
        """
        desired_speed_ms = desired_speed * 0.514444     # Convert knots to m/s (more on this later)
        speed_diff = desired_speed_ms - self.current_speed
        
        if speed_diff > 0:
            # Accelerating
            max_accel = self.aircraft_type.max_acceleration
            
            # If we have a known stop point, check if we need to limit acceleration
            if distance_to_stop is not None:
                # Calculate stopping distance at max speed
                stopping_dist = (desired_speed_ms ** 2) / (2 * self.aircraft_type.max_deceleration)
                if stopping_dist > distance_to_stop:
                    # Limit acceleration to ensure we can stop in time
                    max_accel = min(max_accel, 
                                  self.aircraft_type.max_deceleration * distance_to_stop / stopping_dist)
            
            return min(max_accel, speed_diff)
        else:
            # Decelerating
            return max(-self.aircraft_type.max_deceleration, speed_diff)
    
    def update_speed(self, dt: float, acceleration: float) -> float:
        """
        Update aircraft speed based on physics
        
        Args:
            dt: Time step in seconds
            acceleration: Current acceleration in m/s²
            
        Returns:
            New speed in knots
        """
        # Update speed
        new_speed_ms = self.current_speed + acceleration * dt
        
        # Enforce speed limits
        new_speed_ms = max(0.0, min(new_speed_ms, self._max_speed_ms))
        
        # Update internal state
        self.current_speed = new_speed_ms
        
        # Return speed in knots
        return new_speed_ms / 0.514444     # Convert m/s to knots (I know that I convert it twice but I didnt want to complicate equations)

# Common aircraft type definitions (might be moved to an external file later)
# Also all these values come from a website that I found, I might be wrong but I'll trust it
AIRCRAFT_TYPES = {
    "A320": AircraftType(
        size=AircraftSize.MEDIUM,
        max_taxi_speed=20,        # knots
        max_acceleration=1.0,     # m/s²
        max_deceleration=2.0,     # m/s²
    ),
    "B747": AircraftType(
        size=AircraftSize.HEAVY,
        max_taxi_speed=20,        # knots
        max_acceleration=0.8,     # m/s²
        max_deceleration=1.5,     # m/s²
    ),
    # Add more aircraft types as needed
} 