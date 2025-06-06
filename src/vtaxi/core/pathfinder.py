"""
Test Movement Script
Finds the shortest path through segments matching the given taxiway sequence.

Basic usage:
python -m vtaxi.core.pathfinder --type arrival --path [W37,L4,W2,V06] --airport_config WEST
python -m vtaxi.core.pathfinder --type arrival --path [W42,L42,LR,W3,P13] --airport_config EAST
python -m vtaxi.core.pathfinder --type departure --path [A22,W2,L4,W37] --airport_config EAST
python -m vtaxi.core.pathfinder --type departure --path [A22,W2,L4,W37] --airport_config WEST

"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from heapq import heappush, heappop
from dataclasses import dataclass
from enum import Enum

class MovementType(Enum):
    """Type of aircraft movement."""
    ARRIVAL = "arrival"
    DEPARTURE = "departure"

@dataclass
class TaxiSegment:
    """Helper class to store segment information."""
    segment_id: str
    name: str
    start_node: str
    end_node: str
    length: float
    segment_type: str = "taxiway"  # taxiway, runway, parking_position
    
    def __repr__(self):
        return f"{self.segment_id} ({self.name}): {self.start_node} -> {self.end_node}"

class TaxiPath:
    """Represents a complete taxi path with segments and metadata."""
    def __init__(self):
        self.segments: List[str] = []  # List of segment IDs
        self.total_distance: float = 0.0
        self.waypoints: List[str] = []  # List of waypoint nodes visited
        
    def add_segment(self, segment_id: str, distance: float) -> None:
        """Add a segment to the path."""
        self.segments.append(segment_id)
        self.total_distance += distance
        
    def add_waypoint(self, node_id: str) -> None:
        """Add a waypoint to the path."""
        self.waypoints.append(node_id)

class Airport:
    """Class to manage airport layout and path finding."""
    
    def __init__(self, geojson_file: Path, config_file: Path, airport_config: str = 'WEST'):
        """Initialize airport with layout and configuration data."""
        self.geojson_file = geojson_file
        self.config_file = config_file
        self.config: Dict = {}
        self.segments_by_name: Dict[str, List[TaxiSegment]] = {}
        self.all_segments: List[TaxiSegment] = []
        self.graph: Dict[str, List[Tuple[str, str, float]]] = {}  # node -> [(next_node, segment_id, length)]
        self.airport_config = airport_config
        
        self._load_data()
        
    def _load_data(self) -> None:
        """Load airport data from files."""
        # Load configuration
        if not self.config_file.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_file}")
        with open(self.config_file, 'r') as f:
            self.config = json.load(f)
            
        # Load GeoJSON
        if not self.geojson_file.exists():
            raise FileNotFoundError(f"GeoJSON file not found: {self.geojson_file}")
        with open(self.geojson_file, 'r') as f:
            data = json.load(f)
            
        # Process segments
        for feature in data['features']:
            if feature['geometry']['type'] == 'LineString':
                props = feature['properties']
                if 'name' in props and props['name']:
                    segment = TaxiSegment(
                        props['segment_id'],
                        props['name'],
                        props['start_node'],
                        props['end_node'],
                        props['length'],
                        props.get('segment_type', 'taxiway')
                    )
                    if props['name'] not in self.segments_by_name:
                        self.segments_by_name[props['name']] = []
                    self.segments_by_name[props['name']].append(segment)
                    self.all_segments.append(segment)
                    
        # Build graph
        for segment in self.all_segments:
            if segment.start_node not in self.graph:
                self.graph[segment.start_node] = []
            if segment.end_node not in self.graph:
                self.graph[segment.end_node] = []
            # Add both directions since we can traverse segments either way
            self.graph[segment.start_node].append((segment.end_node, segment.segment_id, segment.length))
            self.graph[segment.end_node].append((segment.start_node, segment.segment_id, segment.length))
            
    def validate_movement(self, movement_type: MovementType, points: List[str]) -> bool:
        """Validate movement points against airport configuration."""
        if len(points) < 2:
            print("Error: Path must contain at least start and end points")
            return False
            
        if movement_type == MovementType.ARRIVAL:
            # Validate runway exit
            runway_config = self.config['runway_configurations'][self.airport_config]
            exit_found = False
            exit_point = points[0]
            for exit_name, exit_node in runway_config['exits']:
                if exit_point == exit_name:
                    exit_found = True
                    break
            if not exit_found:
                print(f"Error: First point {exit_point} is not a valid runway exit for {self.airport_config} configuration")
                print(f"Valid exits are: {[exit_name for exit_name, _ in runway_config['exits']]}")
                return False
                
            # Validate gate
            gate_id = points[-1]
            gate_found = False
            for terminal in self.config['gates']['terminals'].values():
                for gate in terminal['gates']:
                    if gate['gate_id'] == gate_id:
                        gate_found = True
                        break
                if gate_found:
                    break
            if not gate_found:
                print(f"Error: Last point {gate_id} is not a valid gate")
                return False
                
        else:  # departure
            # Validate gate
            gate_id = points[0]
            gate_found = False
            for terminal in self.config['gates']['terminals'].values():
                for gate in terminal['gates']:
                    if gate['gate_id'] == gate_id:
                        gate_found = True
                        break
                if gate_found:
                    break
            if not gate_found:
                print(f"Error: First point {gate_id} is not a valid gate")
                return False
                
            # Validate runway entrance
            runway_config = self.config['runway_configurations'][self.airport_config]
            entrance_found = False
            entrance_point = points[-1]
            for entrance_name, entrance_node in runway_config['entrances']:
                if entrance_point == entrance_name:
                    entrance_found = True
                    break
            if not entrance_found:
                print(f"Error: Last point {entrance_point} is not a valid runway entrance for {self.airport_config} configuration")
                print(f"Valid entrances are: {[entrance_name for entrance_name, _ in runway_config['entrances']]}")
                return False
                
        return True
        
    def find_path(self, points: List[str], movement_type: MovementType) -> Optional[TaxiPath]:
        """Find shortest path through waypoints."""
        if not self.validate_movement(movement_type, points):
            return None
            
        def get_segment_nodes(waypoint: str, enforce_node: Optional[str] = None) -> Set[str]:
            """
            Get all nodes connected to segments of a waypoint.
            
            Args:
                waypoint: The waypoint identifier
                enforce_node: If provided, only return this specific node
            """
            # If a specific node is enforced, return only that
            if enforce_node is not None:
                return {enforce_node}
            
            # For runway entrances/exits, use the specific node from config
            if movement_type == MovementType.ARRIVAL and waypoint == points[0]:
                # First point is runway exit
                for exit_name, exit_node in self.config['runway_configurations'][self.airport_config]['exits']:
                    if waypoint == exit_name:
                        return {exit_node}
            elif movement_type == MovementType.DEPARTURE and waypoint == points[-1]:
                # Last point is runway entrance
                for entrance_name, entrance_node in self.config['runway_configurations'][self.airport_config]['entrances']:
                    if waypoint == entrance_name:
                        return {entrance_node}
            
            # For other waypoints, get all connected nodes
            nodes = set()
            for segment in self.segments_by_name.get(waypoint, []):
                nodes.add(segment.start_node)
                nodes.add(segment.end_node)
            return nodes
            
        def dijkstra_multi_target(start_nodes: List[str], target_nodes: Set[str], 
                                forbidden_segments: Set[str] = None,
                                allowed_segment_names: Optional[Set[str]] = None) -> Dict[str, Tuple[float, List[str]]]:
            """
            Find shortest paths from start_nodes to any target node.
            
            Args:
                start_nodes: List of starting node IDs
                target_nodes: Set of target node IDs
                forbidden_segments: Set of segment IDs that cannot be used
                allowed_segment_names: If provided, only use segments with these names
            """
            if forbidden_segments is None:
                forbidden_segments = set()
                
            distances = {node: (float('inf'), []) for node in self.graph}  # (distance, path)
            for start in start_nodes:
                if start not in self.graph:
                    print(f"WARNING - Start node {start} not in graph!")
                    continue
                distances[start] = (0, [])
            
            pq = [(0, start, []) for start in start_nodes if start in self.graph]  # (distance, node, path)
            found_targets = set()
            
            while pq and len(found_targets) < len(target_nodes):
                dist, current, path = heappop(pq)
                
                if current in target_nodes:
                    found_targets.add(current)
                
                # If we've found a better path already, skip
                if dist > distances[current][0]:
                    continue
                    
                # Try all neighbors
                for next_node, segment_id, length in self.graph[current]:
                    if segment_id in forbidden_segments:
                        continue
                        
                    # Skip if segment name not in allowed set
                    segment = next(s for s in self.all_segments if s.segment_id == segment_id)
                    if allowed_segment_names and segment.name not in allowed_segment_names:
                        continue
                        
                    new_dist = dist + length
                    new_path = path + [segment_id]
                    
                    if new_dist < distances[next_node][0]:
                        distances[next_node] = (new_dist, new_path)
                        heappush(pq, (new_dist, next_node, new_path))
            
            return distances
            
        # Create new path
        path = TaxiPath()
        used_segments: Set[str] = set()  # Don't add the first segment here anymore
        
        # Add initial segment (runway exit or gate)
        first_segments = self.segments_by_name.get(points[0], [])
        if not first_segments:
            print(f"No segments found for {points[0]}")
            return None
            
        first_segment = None
        first_node = None
        gate_node = None
        
        if movement_type == MovementType.DEPARTURE:
            # For departures, get the exact node_id from the gate configuration
            gate_id = points[0]
            # Search through all terminals to find the matching gate
            for terminal in self.config['gates']['terminals'].values():
                for gate in terminal['gates']:
                    if gate['gate_id'] == gate_id:
                        gate_node = gate['node_id']
                        break
                if gate_node:
                    break
            
            if gate_node:
                # Find the segment connected to this node
                for seg in first_segments:
                    if gate_node in [seg.start_node, seg.end_node]:
                        first_segment = seg
                        first_node = gate_node
                        break
        else:  # ARRIVAL
            # For arrivals, use the exit node of runway segment
            for seg in first_segments:
                if seg.segment_type == "runway":
                    first_segment = seg
                    first_node = seg.end_node
                    break
                
        if not first_segment:
            first_segment = first_segments[0]
            first_node = first_segment.end_node
            
        path.add_segment(first_segment.segment_id, first_segment.length)
        # Only add to used_segments if not a departure starting from a gate
        if not (movement_type == MovementType.DEPARTURE and first_node == gate_node):
            used_segments.add(first_segment.segment_id)
        
        last_node = first_node
        
        # Find path through waypoints
        current_waypoint_idx = 0
        while current_waypoint_idx < len(points) - 1:
            current_waypoint = points[current_waypoint_idx]
            next_waypoint = points[current_waypoint_idx + 1]
            
            # Get nodes for the next waypoint
            enforce_node = None
            if movement_type == MovementType.DEPARTURE and next_waypoint == points[-1]:
                # If this is the last waypoint and we're departing, enforce the entrance node
                for entrance_name, node_id in self.config['runway_configurations'][self.airport_config]['entrances']:
                    if next_waypoint == entrance_name:
                        enforce_node = node_id
                        break
            
            # Get all nodes connected to the next waypoint
            target_nodes = get_segment_nodes(next_waypoint, enforce_node)
            
            # When moving between waypoints, only use segments from those waypoints
            allowed_segments = {current_waypoint, next_waypoint}
            
            # Find shortest path to any node of the next waypoint
            distances = dijkstra_multi_target([last_node], target_nodes, used_segments, allowed_segments)
            
            # Find the best target node and its path
            best_target = None
            best_dist = float('inf')
            best_path = None
            
            for target_node in target_nodes:
                dist, segment_path = distances[target_node]
                if dist < best_dist:
                    # Verify all segments in path belong to either current or next waypoint
                    valid_path = True
                    for segment_id in segment_path:
                        segment = next(s for s in self.all_segments if s.segment_id == segment_id)
                        if segment.name not in allowed_segments:
                            valid_path = False
                            break
                    
                    if valid_path:
                        best_dist = dist
                        best_path = segment_path
                        best_target = target_node
            
            if best_path is None:
                print(f"No valid path found from {current_waypoint} to {next_waypoint}")
                return None
                
            # Add path segments
            for segment_id in best_path:
                segment = next(s for s in self.all_segments if s.segment_id == segment_id)
                path.add_segment(segment_id, segment.length)
                used_segments.add(segment_id)
                
            last_node = best_target
            current_waypoint_idx += 1
            
        # Add final segment if needed (gate or runway entrance)
        if movement_type == MovementType.DEPARTURE:
            # For departures to runway, use the specific entrance node from config
            entrance_point = points[-1]
            entrance_node = None
            for entrance_name, node_id in self.config['runway_configurations'][self.airport_config]['entrances']:
                if entrance_point == entrance_name:
                    entrance_node = node_id
                    break
            
            if entrance_node:
                # Find the segment that connects to our last node and the specified entrance node
                last_segments = self.segments_by_name.get(points[-1], [])
                for seg in last_segments:
                    if entrance_node in [seg.start_node, seg.end_node] and last_node in [seg.start_node, seg.end_node]:
                        path.add_segment(seg.segment_id, seg.length)
                        break
        else:  # ARRIVAL
            # For arrivals to gates, use the specific gate segment
            gate_id = points[-1]
            gate_node = None
            for terminal in self.config['gates']['terminals'].values():
                for gate in terminal['gates']:
                    if gate['gate_id'] == gate_id:
                        gate_node = gate['node_id']
                        break
                if gate_node:
                    break
            
            if gate_node:
                # Find the segment that connects to our last node and the gate node
                last_segments = self.segments_by_name.get(points[-1], [])
                for seg in last_segments:
                    if gate_node in [seg.start_node, seg.end_node] and last_node in [seg.start_node, seg.end_node]:
                        path.add_segment(seg.segment_id, seg.length)
                        break
            
        return path

def get_segment_path(args):
    """Find shortest path through segments matching the taxiway sequence."""
    # Load airport data
    data_dir = Path(args.airport_data).parent
    geojson_file = data_dir / 'LFPO.geojson'
    config_file = data_dir / 'LFPO.json'
    
    # Create airport instance
    try:
        airport = Airport(geojson_file, config_file, args.airport_config)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return
        
    # Parse path points
    points = args.path.strip('[]').split(',')
    points = [p.strip() for p in points]
    
    # Find path
    movement_type = MovementType.ARRIVAL if args.type == 'arrival' else MovementType.DEPARTURE
    print(f"\nProcessing {movement_type.value} path")
    print("Waypoints:", ' -> '.join(points))
    
    path = airport.find_path(points, movement_type)
    
    if path:
        print("\nShortest path found:")
        # Track segments we've already printed to avoid duplicates
        printed_segments = set()
        segment_count = 1
        
        for segment_id in path.segments:
            if segment_id not in printed_segments:
                segment = next(s for s in airport.all_segments if s.segment_id == segment_id)
                print(f"{segment_count}. {segment}")
                printed_segments.add(segment_id)
                segment_count += 1
        
        print(f"\nTotal path length: {path.total_distance:.1f}m")
    else:
        print("\nNo valid path found through all waypoints!")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Find shortest path through segments matching the taxiway sequence'
    )
    
    parser.add_argument(
        '--type',
        choices=['arrival', 'departure'],
        required=True,
        help='Type of movement (arrival: runway->gate, departure: gate->runway)'
    )

    parser.add_argument(
        '--airport_config',
        choices=['EAST', 'WEST'],
        default='WEST',
        help='Airport configuration (EAST or WEST)'
    )
    
    parser.add_argument(
        '--path',
        required=True,
        help='Comma-separated list of points in brackets (e.g., [W37,L4,W2,V06])'
    )
    
    parser.add_argument(
        '--airport-data',
        default=str(Path(__file__).parent.parent / 'data' / 'LFPO.json'),
        help='Path to airport data directory or config file'
    )
    
    args = parser.parse_args()
    get_segment_path(args)

if __name__ == '__main__':
    main() 