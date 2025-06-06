import json
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.collections import LineCollection
import numpy as np

def load_airport_data():
    """Load airport data from GeoJSON file"""
    data_dir = Path(__file__).parent.parent / 'data'
    geojson_file = data_dir / 'LFPO.geojson'
    config_file = data_dir / 'LFPO.json'
    
    with open(geojson_file, 'r') as f:
        geojson_data = json.load(f)
    with open(config_file, 'r') as f:
        config_data = json.load(f)
        
    return geojson_data, config_data

def create_segment_collections(geojson_data):
    """Create collections of segments by type"""
    segments = {
        'runway': [],
        'taxiway': [],
        'parking_position': [],
        'coordinates': []  # Store all coordinates to calculate bounds
    }
    
    # Color mapping for different segment types
    colors = {
        'runway': '#404040',      # Dark gray
        'taxiway': '#808080',     # Medium gray
        'parking_position': '#A0A0A0'  # Light gray
    }
    
    # Line width mapping (magic numbers)
    widths = {
        'runway': 6,  # Made runways thicker
        'taxiway': 3,  # Made taxiways thicker
        'parking_position': 1.5  # Made parking positions slightly thicker
    }
    
    for feature in geojson_data['features']:
        if feature['geometry']['type'] == 'LineString':
            coords = feature['geometry']['coordinates']
            segment_type = feature['properties'].get('segment_type', 'taxiway')
            
            # Add to type-specific collection
            if segment_type in segments:
                segments[segment_type].append(coords)
            
            # I think this adds to overall coordinates but I'm not sure and I'm too lazy to check
            segments['coordinates'].extend(coords)
    
    # Create line collections for each type
    collections = {}
    for segment_type in ['runway', 'taxiway', 'parking_position']:
        if segments[segment_type]:
            collections[segment_type] = LineCollection(
                segments[segment_type],
                colors=colors[segment_type],
                linewidths=widths[segment_type],
                label=segment_type.replace('_', ' ').title()
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

def visualize_airport():
    """Create and display airport visualization"""
    # Load data
    geojson_data, config_data = load_airport_data()
    
    # Create figure with white background
    plt.figure(figsize=(12, 8), facecolor='white')
    ax = plt.gca()
    
    # Create collections and get bounds
    collections, bounds = create_segment_collections(geojson_data)
    
    # Add collections to plot
    for collection in collections.values():
        ax.add_collection(collection)
    
    # Set bounds with padding
    padding = 0.001  # About 100m in geographic coordinates (yeah yeah magic numbers are bad, I know !)
    ax.set_xlim(bounds['min_x'] - padding, bounds['max_x'] + padding)
    ax.set_ylim(bounds['min_y'] - padding, bounds['max_y'] + padding)
    
    # Equal aspect ratio for accurate shape
    ax.set_aspect('equal')
    
    # Remove axes, grid, and borders
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    
    # Add title and legend
    plt.title('Paris-Orly Airport (LFPO) Layout', pad=20, fontsize=14)
    plt.legend(loc='upper right', frameon=False)
    
    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    visualize_airport() 