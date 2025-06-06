'''
python -m vtaxi.tests.visualize_path --type arrival --path [W42,L42,LR,W3,P13] --airport_config EAST
python -m vtaxi.tests.visualize_path --type departure --path [A22,W2,L4,W37] --airport_config EAST
'''


import json
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import numpy as np
import argparse
from ..core.pathfinder import Airport, MovementType

def create_segment_collections(geojson_data, highlight_segments=None):
    """Create collections of segments by type, with optional highlighted path"""
    segments = {
        'runway': [],
        'taxiway': [],
        'parking_position': [],
        'path': [],  # For highlighted path
        'coordinates': []
    }
    
    # Color mapping for different segment types
    colors = {
        'runway': '#404040',      # Dark gray
        'taxiway': '#808080',     # Medium gray
        'parking_position': '#A0A0A0',  # Light gray
        'path': '#FF0000'         # Red for highlighted path
    }
    
    # Line width mapping (magic numbers)
    widths = {
        'runway': 6,
        'taxiway': 3,
        'parking_position': 1.5,
        'path': 4  # Make path slightly thinner than runways but thicker than taxiways 
    }
    
    highlight_segment_ids = set(highlight_segments) if highlight_segments else set()
    
    for feature in geojson_data['features']:
        if feature['geometry']['type'] == 'LineString':
            coords = feature['geometry']['coordinates']
            segment_type = feature['properties'].get('segment_type', 'taxiway')
            segment_id = feature['properties'].get('segment_id')
            
            # Add to type-specific collection
            if segment_type in segments:
                segments[segment_type].append(coords)
            
            # If this segment is part of our path, add it to path collection
            if segment_id in highlight_segment_ids:
                segments['path'].append(coords)
            
            segments['coordinates'].extend(coords)
    
    # Create line collections for each type
    collections = {}
    for segment_type in ['runway', 'taxiway', 'parking_position', 'path']:
        if segments[segment_type]:
            collections[segment_type] = LineCollection(
                segments[segment_type],
                colors=colors[segment_type],
                linewidths=widths[segment_type],
                label=segment_type.replace('_', ' ').title() if segment_type != 'path' else 'Taxi Path',
                zorder=4 if segment_type == 'path' else 1  # Make path appear on top
            )
    
    # Calculate bounds
    all_coords = np.array(segments['coordinates'])
    bounds = {
        'min_x': np.min(all_coords[:, 0]),
        'max_x': np.max(all_coords[:, 0]),
        'min_y': np.min(all_coords[:, 1]),
        'max_y': np.max(all_coords[:, 1])
    }
    
    return collections, bounds

def visualize_path(path_segments=None):
    """Create and display airport visualization with optional path highlight"""
    # Load airport data
    data_dir = Path(__file__).parent.parent / 'data'
    geojson_file = data_dir / 'LFPO.geojson'
    
    # Load GeoJSON data
    with open(geojson_file, 'r') as f:
        geojson_data = json.load(f)
    
    # Create figure with white background
    plt.figure(figsize=(12, 8), facecolor='white')
    ax = plt.gca()
    
    # Create collections and get bounds
    collections, bounds = create_segment_collections(geojson_data, path_segments)
    
    # Add collections to plot
    for collection in collections.values():
        ax.add_collection(collection)
    
    # Set bounds with padding
    padding = 0.001  # About 100m in geographic coordinates
    ax.set_xlim(bounds['min_x'] - padding, bounds['max_x'] + padding)
    ax.set_ylim(bounds['min_y'] - padding, bounds['max_y'] + padding)
    
    # Equal aspect ratio for accurate shape
    ax.set_aspect('equal')
    
    # Remove axes and borders
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    
    # Add title and legend
    plt.title('Paris-Orly Airport (LFPO) Layout', pad=20, fontsize=14)
    if path_segments:  # Only show legend if we're displaying a path
        plt.legend(loc='upper right', frameon=False)
    
    plt.tight_layout()
    plt.show()

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Visualize a taxi path through the airport'
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
    
    args = parser.parse_args()
    
    # Initialize airport
    data_dir = Path(__file__).parent.parent / 'data'
    geojson_file = data_dir / 'LFPO.geojson'
    config_file = data_dir / 'LFPO.json'
    airport = Airport(geojson_file, config_file, args.airport_config)
    
    # Parse path points
    points = args.path.strip('[]').split(',')
    points = [p.strip() for p in points]
    
    # Find path
    movement_type = MovementType.ARRIVAL if args.type == 'arrival' else MovementType.DEPARTURE
    path = airport.find_path(points, movement_type)
    
    if path:
        # Visualize the path
        visualize_path(path.segments)
    else:
        print("No valid path found!")

if __name__ == '__main__':
    main() 