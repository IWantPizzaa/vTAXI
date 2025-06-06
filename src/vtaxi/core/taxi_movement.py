from dataclasses import dataclass
from typing import List, Dict
from .aircraft_physics import AircraftPhysics
from .pathfinder import TaxiPath, TaxiSegment

# Yeah yeah, I use magic numbers but it works so I'm not gonna change it

@dataclass
class MovementPoint:
    """Represents a point along the taxi path with physical parameters"""
    position: float          # Distance from start of segment in meters
    time: float             # Time since start in seconds
    speed: float            # Current speed in knots
    acceleration: float     # Current acceleration in m/s²
    segment_id: str         # Current segment ID
    node_id: str           # Current or next node ID
    heading: float          # Current heading in degrees

@dataclass
class SegmentConstraints:
    """Physical constraints for a taxi segment"""
    max_speed: float        # Maximum allowed speed in knots
    entry_speed: float      # Maximum entry speed in knots
    exit_speed: float       # Maximum exit speed in knots
    length: float          # Segment length in meters

class TaxiMovement:
    """Handles movement along a taxi path"""
    
    def __init__(self, taxi_path: TaxiPath, aircraft: AircraftPhysics, segments: Dict[str, TaxiSegment]):
        self.path = taxi_path
        self.aircraft = aircraft
        self.segments = segments
        self.movement_points: List[MovementPoint] = []
        self.segment_constraints: Dict[str, SegmentConstraints] = {}
        
        # Calculate constraints for each segment
        self._calculate_segment_constraints()
    
    def _calculate_segment_constraints(self) -> None:
        """Calculate physical constraints for each segment in the path"""

        # This was build to incorporate aircraft max speed and segment type,
        # eaven thought there are no segement constraints in the pathfinder nor aircraft physics nor anything else actually.
        # I keep it here if you would like to refactor the code for a different airport having specific sections 
        # with speed limits, on way taxiways, out off order sections, etc.
        # I will keep it here for now, but it might be removed later

        for i, segment_id in enumerate(self.path.segments):
            segment = self.segments[segment_id]
            
            # Base max speed on segment type and aircraft constraints
            base_max_speed = self.aircraft.aircraft_type.max_taxi_speed
            if segment.segment_type == "runway":
                base_max_speed *= 1.2  # Allow higher speeds on runways (magic number)
            elif "rapid" in segment.name.lower():
                base_max_speed *= 1.1  # Allow higher speeds on rapid exit taxiways (magic number)
            
            # Entry speed is limited by previous segment's exit speed
            entry_speed = min(base_max_speed, 
                            self.segment_constraints[self.path.segments[i-1]].exit_speed if i > 0 else base_max_speed)
            
            # Exit speed is limited by next segment or stop point
            exit_speed = base_max_speed
            
            # Final segment should come to a stop
            if i == len(self.path.segments) - 1:
                exit_speed = 0.0
            
            self.segment_constraints[segment_id] = SegmentConstraints(
                max_speed=base_max_speed,
                entry_speed=entry_speed,
                exit_speed=exit_speed,
                length=segment.length
            )
    
    def calculate_movement_profile(self, time_step: float = 1.0) -> List[MovementPoint]:
        """
        Calculate a complete movement profile with speed and time for each point.
        
        Args:
            time_step: Time step in seconds for the simulation
            
        Returns:
            List of MovementPoint objects describing the aircraft's state over time
        """
        self.movement_points = []
        current_time = 0.0
        current_speed = 0.0
        current_position = 0.0
        
        for i, segment_id in enumerate(self.path.segments):
            segment = self.segments[segment_id]
            constraints = self.segment_constraints[segment_id]
            
            # Start from beginning of segment
            position_in_segment = 0.0
            
            while position_in_segment < constraints.length:
                # Calculate target speed based on position in segment
                progress = position_in_segment / constraints.length
                target_speed = constraints.entry_speed + (constraints.exit_speed - constraints.entry_speed) * progress
                
                # Calculate safe acceleration/deceleration
                distance_remaining = constraints.length - position_in_segment
                acceleration = self.aircraft.calculate_acceleration(
                    target_speed,
                    distance_to_stop=distance_remaining if i == len(self.path.segments) - 1 else None
                )
                
                # Update speed and position
                new_speed = self.aircraft.update_speed(time_step, acceleration)
                avg_speed = (current_speed + new_speed) / 2
                distance_moved = avg_speed * 0.514444 * time_step  # Convert knots to m/s
                
                # Record movement point
                self.movement_points.append(MovementPoint(
                    position=current_position + position_in_segment,
                    time=current_time,
                    speed=current_speed,
                    acceleration=acceleration,
                    segment_id=segment_id,
                    node_id=segment.end_node if progress > 0.5 else segment.start_node
                ))
                
                # Update for next step
                current_speed = new_speed
                position_in_segment += distance_moved
                current_time += time_step
            
            # Update total position at end of segment
            current_position += constraints.length
        
        return self.movement_points 