"""
Airport Layout Processor
Processes airport data from OpenStreetMap GeoJSON format into a segmented network format.

This script combines functionality from:
- airport_processor.py
- airport_layout.py
- process_airport.py
- geometry.py
- geo_segmentation.py

Main features:
- Processes raw GeoJSON data from OpenStreetMap
- Creates a segmented network of taxiways and runways
- Identifies gates, parking positions, and runway exits
- Generates two output files:
  1. LFPO.geojson: Network data with nodes and segments
  2. LFPO.json: Airport configuration with runways, gates, etc.
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from shapely.geometry import shape, Point, LineString
from geopy.distance import geodesic

@dataclass
class Node:
    """Network node representing an intersection or endpoint."""
    node_id: str
    coordinates: Tuple[float, float]
    connected_segments: List[str]
    node_type: str = "intersection"  # intersection, runway_exit, parking_exit, gate
    gate_info: Optional[dict] = None

@dataclass
class Segment:
    """Network segment representing a taxiway or parking section."""
    segment_id: str
    start_node: str
    end_node: str
    geometry: List[Tuple[float, float]]
    segment_type: str  # taxiway, parking_position, runway
    name: str = ""
    length: float = 0.0
    heading: float = 0.0

class AirportProcessor:
    """Main class for processing airport layout data."""
    
    def __init__(self, input_geojson: str, input_config: str):
        """
        Initialize processor with input files.
        
        Args:
            input_geojson: Path to raw GeoJSON file from OpenStreetMap
            input_config: Path to airport configuration JSON
        """
        self.input_geojson = Path(input_geojson)
        self.input_config = Path(input_config)
        self.nodes: Dict[str, Node] = {}
        self.segments: Dict[str, Segment] = {}
        self.config_data: dict = {}
        self.gates: Dict[str, dict] = {}
        
        # Known runway entrance/exit points for LFPO
        self.runway_points = {
            'W34', 'W35', 'W36', 'W37', 'W4', 
            'W41', 'W42', 'W43', 'W44'
        }
        
    def load_data(self) -> None:
        """Load input data from files."""
        # Load configuration
        with open(self.input_config) as f:
            self.config_data = json.load(f)
            
        # Load GeoJSON
        with open(self.input_geojson) as f:
            self.raw_data = json.load(f)
            
    def process_layout(self) -> None:
        """Process airport layout into segmented network."""
        features = []
        
        # Filter and process features
        for feature in self.raw_data['features']:
            props = feature['properties']
            geom = feature['geometry']
            
            # Skip aprons
            if props.get('aeroway') == 'apron':
                continue
                
            if props.get('aeroway') in ['taxiway', 'runway', 'parking_position']:
                if geom['type'] == 'LineString':
                    features.append({
                        'geometry': geom,
                        'properties': props
                    })
                    
        # Process features into network
        self._create_network(features)
        
    def _get_way_coordinates(self, node_ids: List[int]) -> List[Tuple[float, float]]:
        """Convert node IDs to coordinates - DEPRECATED, left for reference."""
        coords = []
        for node_id in node_ids:
            node = next((n for n in self.raw_data['elements'] 
                        if n['type'] == 'node' and n['id'] == node_id), None)
            if node:
                coords.append((node['lon'], node['lat']))
        return coords
        
    def _create_network(self, features: List[dict]) -> None:
        """Create network from features."""
        # First pass: collect all points
        points = []
        lines = []
        
        for feature in features:
            geom = shape(feature['geometry'])
            props = feature['properties']
            
            if not isinstance(geom, LineString):
                continue
                
            # Add endpoints
            points.extend([Point(geom.coords[0]), Point(geom.coords[-1])])
            lines.append((geom, props))
            
        # Find intersections
        for i, (line1, _) in enumerate(lines):
            for line2, _ in lines[i+1:]:
                if line1.intersects(line2):
                    intersection = line1.intersection(line2)
                    if isinstance(intersection, Point):
                        points.append(intersection)
                        
        # Create nodes
        unique_points = {}
        for pt in points:
            key = self._round_point(pt)
            if key not in unique_points:
                node_id = f"N{len(unique_points):05d}"
                node = Node(
                    node_id=node_id,
                    coordinates=key,
                    connected_segments=[]
                )
                unique_points[key] = node
                self.nodes[node_id] = node
                
        # Create segments
        for line, props in lines:
            self._create_segments(line, props, unique_points)
            
        # Identify special nodes
        self._identify_special_nodes()
        
    def _round_point(self, pt: Point, precision: int = 7) -> Tuple[float, float]:
        """Round point coordinates to specified precision."""
        return (round(pt.x, precision), round(pt.y, precision))
        
    def _create_segments(self, line: LineString, props: dict, points: Dict) -> None:
        """Create segments from line."""
        coords = list(line.coords)
        points_on_line = []
        
        # Find all points on this line
        for pt_coords, node in points.items():
            point = Point(pt_coords)
            if point.distance(line) < 1e-8:  # Small threshold
                points_on_line.append((point.distance(Point(coords[0])), node))
                
        # Sort points by distance from start
        points_on_line.sort()
        
        # Create segments between consecutive points
        for i in range(len(points_on_line) - 1):
            start_node = points_on_line[i][1]
            end_node = points_on_line[i + 1][1]
            
            segment_id = f"S{len(self.segments):05d}"
            segment = Segment(
                segment_id=segment_id,
                start_node=start_node.node_id,
                end_node=end_node.node_id,
                geometry=self._extract_segment_geometry(line, start_node.coordinates, end_node.coordinates),
                segment_type=props.get('aeroway', 'unknown'),
                name=props.get('ref', '')
            )
            
            # Calculate length and heading
            segment.length = self._calculate_length(segment.geometry)
            segment.heading = self._calculate_heading(segment.geometry)
            
            self.segments[segment_id] = segment
            start_node.connected_segments.append(segment_id)
            end_node.connected_segments.append(segment_id)
            
    def _extract_segment_geometry(self, line: LineString, start: Tuple[float, float], 
                                end: Tuple[float, float]) -> List[Tuple[float, float]]:
        """Extract geometry between two points on a line."""
        coords = list(line.coords)
        start_pt = Point(start)
        end_pt = Point(end)
        
        # Find nearest points
        start_idx = min(range(len(coords)), 
                       key=lambda i: Point(coords[i]).distance(start_pt))
        end_idx = min(range(len(coords)), 
                     key=lambda i: Point(coords[i]).distance(end_pt))
        
        if start_idx > end_idx:
            start_idx, end_idx = end_idx, start_idx
            
        return coords[start_idx:end_idx + 1]
        
    def _calculate_length(self, coords: List[Tuple[float, float]]) -> float:
        """Calculate length of a line in meters."""
        total = 0.0
        for i in range(len(coords) - 1):
            p1 = coords[i][::-1]  # Convert to (lat, lon)
            p2 = coords[i + 1][::-1]
            total += geodesic(p1, p2).meters
        return total
        
    def _calculate_heading(self, coords: List[Tuple[float, float]]) -> float:
        """Calculate heading in degrees."""
        if len(coords) < 2:
            return 0.0
        start = coords[0]
        end = coords[-1]
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        heading = math.degrees(math.atan2(dy, dx)) % 360
        return heading
        
    def _identify_special_nodes(self) -> None:
        """Identify and mark special nodes."""
        # Find runway exit nodes
        for segment in self.segments.values():
            if segment.name in self.runway_points:
                for node_id in [segment.start_node, segment.end_node]:
                    self.nodes[node_id].node_type = "runway_exit"
                    
        # Find parking exit nodes
        parking_exits = set()
        for pos_data in self.config_data.get('parking_positions', {}).values():
            exit_taxiway = pos_data.get('exit_taxiway')
            if exit_taxiway:
                parking_exits.add(exit_taxiway)
                
        for segment in self.segments.values():
            if segment.name in parking_exits:
                for node_id in [segment.start_node, segment.end_node]:
                    if self.nodes[node_id].node_type == "intersection":
                        self.nodes[node_id].node_type = "parking_exit"
                        
        # Find gate nodes
        for node in self.nodes.values():
            if len(node.connected_segments) == 1:
                segment = self.segments[node.connected_segments[0]]
                if segment.segment_type == "parking_position":
                    node.node_type = "gate"
                    node.gate_info = {
                        "gate_id": segment.name,
                        "heading": segment.heading,
                        "segment_id": segment.segment_id
                    }
                    self.gates[segment.name] = {
                        "node_id": node.node_id,
                        "coordinates": node.coordinates,
                        "heading": segment.heading,
                        "segment_id": segment.segment_id
                    }
                    
    def export_network(self, output_geojson: str) -> None:
        """Export network to GeoJSON format."""
        features = []
        
        # Export segments
        for segment in self.segments.values():
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": segment.geometry
                },
                "properties": {
                    "segment_id": segment.segment_id,
                    "name": segment.name,
                    "segment_type": segment.segment_type,
                    "start_node": segment.start_node,
                    "end_node": segment.end_node,
                    "length": segment.length,
                    "heading": segment.heading
                }
            })
            
        # Export nodes
        for node in self.nodes.values():
            properties = {
                "node_id": node.node_id,
                "node_type": node.node_type,
                "connected_segments": node.connected_segments
            }
            if node.gate_info:
                properties.update(node.gate_info)
                
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": node.coordinates
                },
                "properties": properties
            })
            
        output = {
            "type": "FeatureCollection",
            "features": features
        }
        
        with open(output_geojson, 'w') as f:
            json.dump(output, f, indent=2)
            
    def export_config(self, output_config: str) -> None:
        """Export configuration to JSON format."""
        # Group gates by terminal
        terminals = {}
        for gate_id, gate_info in self.gates.items():
            # Extract terminal identifier (e.g., 'K' from 'K24')
            terminal_id = ''.join(c for c in gate_id if not c.isdigit())
            if terminal_id not in terminals:
                terminals[terminal_id] = []
            terminals[terminal_id].append({
                "gate_id": gate_id,
                **gate_info
            })
            
        # Define runway configurations
        runway_configs = {
            "WEST": {
                "departure": "24",
                "arrival": "25",
                "entrances": ["W41", "W42"],
                "exits": ["W34", "W35", "W4", "W36", "W37"],
                "alternates": {
                    "departure": "06",
                    "arrival": "07"
                }
            },
            "EAST": {
                "departure": "07",
                "arrival": "06",
                "entrances": ["W37", "W36"],
                "exits": ["W44", "W43", "W42", "W41"],
                "alternates": {
                    "departure": "24",
                    "arrival": "25"
                }
            }
        }
            
        config = {
            "airport_code": "LFPO",
            "name": "Paris-Orly Airport",
            "runways": self.config_data.get("runways", {}),
            "gates": {
                "terminals": {
                    terminal_id: {
                        "gates": sorted(gates, key=lambda x: x["gate_id"])
                    }
                    for terminal_id, gates in terminals.items()
                },
                "total_count": len(self.gates)
            },
            "parking_positions": self.config_data.get("parking_positions", {}),
            "runway_configurations": runway_configs
        }
        
        with open(output_config, 'w') as f:
            json.dump(config, f, indent=2)

def main():
    """Main entry point."""
    # Get paths
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / 'data'
    imported_dir = base_dir / 'data_imported'
    
    # Input files
    input_geojson = imported_dir / 'LFPO.geojson'
    input_config = imported_dir / 'LFPO.json'
    
    # Output files
    output_geojson = data_dir / 'LFPO.geojson'
    output_config = data_dir / 'LFPO.json'
    
    print(f"Processing airport data...")
    print(f"Input GeoJSON: {input_geojson}")
    print(f"Input Config: {input_config}")
    print(f"Output GeoJSON: {output_geojson}")
    print(f"Output Config: {output_config}")
    
    # Create processor
    processor = AirportProcessor(input_geojson, input_config)
    
    # Process data
    processor.load_data()
    processor.process_layout()
    
    # Export results
    processor.export_network(output_geojson)
    processor.export_config(output_config)
    
    print(f"\nProcessing complete.")
    print(f"Network data saved to: {output_geojson}")
    print(f"Configuration saved to: {output_config}")

if __name__ == "__main__":
    main() 