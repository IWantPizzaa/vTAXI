# vTAXI - Virtual Air Traffic Control System for Paris-Orly Airport (LFPO)

A Python-based virtual air traffic control system for simulating and managing ground operations at Paris-Orly Airport (LFPO). The system provides tools for processing airport layout data, managing aircraft movements, and optimizing ground traffic flow.

## Project Structure

```
src/vtaxi/
├── core/                              # Core system components
│   ├── aircraft_physics.py            # Individual aircraft physics (in dev)
│   ├── airport_position assigner.py   # Airport position assigner (in dev)
│   ├── airport_process.py             # Airport data processing
│   ├── pathfinder.py                  # Node and segement pathfinder
│   └── taxi_movement.py               # Taxi movement physics
├── data/                              # Processed airport data
│   ├── LFPO.geojson                   # Network representation
│   └── LFPO.json                      # Airport configuration
├── data_imported/                     # Raw input data
├── tests/                             # Test suite
└── utils/                             # Utility functions
```

## Core Components

### Airport Data Processor (`core/airport_process.py`)

The airport processor converts raw OpenStreetMap GeoJSON data into an optimized network representation for the air traffic control system. Key features:

- Processes raw GeoJSON data from OpenStreetMap
- Creates a segmented network of taxiways and runways
- Identifies gates, parking positions, and runway exits
- Generates network and configuration files

Usage:
```python
from vtaxi.core.airport_process import AirportProcessor

processor = AirportProcessor('data_imported/LFPO.geojson', 'data_imported/LFPO.json')
processor.process_layout()
processor.export_network('data/LFPO.geojson')
processor.export_config('data/LFPO.json')
```

### Pathfinder (`core/pathfinder.py`)

The pathfinder component handles route calculation through the airport's taxiway network. Key features:

- Dijkstra-based pathfinding with support for waypoint sequences
- Handles both arrival (runway to gate) and departure (gate to runway) routes
- Validates paths against airport configuration (EAST/WEST operations)
- Ensures proper runway exit and entrance point usage

Usage:
```bash
# Example for arrival route
python -m vtaxi.core.pathfinder --type arrival --path [W37,L4,W2,V06] --airport_config WEST

# Example for departure route
python -m vtaxi.core.pathfinder --type departure --path [A22,W2,L4,W37] --airport_config EAST
```

### Aircraft Physics (`core/aircraft_physics.py`) *unfinished*

Implements realistic aircraft ground movement physics. Features:

- ICAO weight categories (LIGHT, MEDIUM, HEAVY, SUPER)
- Physical constraints:
  - Maximum taxi speeds
  - Acceleration/deceleration profiles
  - Turning radius limitations
  - Wheelbase and wingspan considerations
- Pre-defined aircraft type configurations (A320, B747 for now but plenty more to come)

### Taxi Movement (`core/taxi_movement.py`) *unfinished*

Manages aircraft movement along taxi paths. Features:

- Combines pathfinding with physics constraints
- Tracks movement points with:
  - Position along path
  - Current speed and acceleration
  - Heading and timing
- Segment-specific speed constraints
- Special handling for:
  - Runway crossings
  - Sharp turns (bugy for now)
  - Rapid exit taxiways

### Visualization Tools

#### Airport Layout (`tests/visualize_airport.py`)

Provides a clean 2D visualization of the airport layout:

Usage:
```bash
python -m vtaxi.tests.visualize_airport
```

#### Path Visualization (`tests/visualize_path.py`)

Extends the airport visualization to show calculated taxi routes:

- Highlights calculated paths in red
- Supports both arrival and departure routes
- Integrates with the pathfinder component

Usage:
```bash
# Visualize an arrival route
python -m vtaxi.tests.visualize_path --type arrival --path [W42,L42,LR,W3,P13] --airport_config EAST

# Visualize a departure route
python -m vtaxi.tests.visualize_path --type departure --path [A22,W2,L4,W37] --airport_config EAST
```

## Data Files

### LFPO.geojson - Network Data

A GeoJSON representation of the airport's ground infrastructure network. Contains two main feature types:

1. **Segments** (LineString features):
   ```json
   {
     "type": "Feature",
     "geometry": {
       "type": "LineString",
       "coordinates": [[lon1, lat1], [lon2, lat2], ...]
     },
     "properties": {
       "segment_id": "S00000",
       "name": "06/24",
       "segment_type": "runway",
       "start_node": "N00000",
       "end_node": "N00001",
       "length": 3649.54,
       "heading": 19.48
     }
   }
   ```

2. **Nodes** (Point features):
   ```json
   {
     "type": "Feature",
     "geometry": {
       "type": "Point",
       "coordinates": [lon, lat]
     },
     "properties": {
       "node_id": "N00000",
       "node_type": "runway_exit",
       "connected_segments": ["S00000", "S00001"],
       "gate_id": "K01",  // Only for gate nodes
       "heading": 154.65  // Only for gate nodes
     }
   }
   ```

### LFPO.json - Airport Configuration

Contains operational parameters and airport configuration:

```json
{
  "airport_code": "LFPO",
  "name": "Paris-Orly Airport",
  "gates": {
    "terminals": {
      "K": {
        "gates": [
          {
            "gate_id": "K01",
            "node_id": "N00566",
            "coordinates": [2.3729856, 48.7432128],
            "heading": 154.65,
            "segment_id": "S00749"
          }
        ]
      }
    }
  },
  "runway_configurations": {
    "WEST": {
      "departure": "24",
      "arrival": "25",
      "entrances": ["W41", "W42"],
      "exits": ["W34", "W35", "W4", "W36", "W37"]
    },
    "EAST": {
      "departure": "07",
      "arrival": "06",
      "entrances": ["W37", "W36"],
      "exits": ["W44", "W43", "W42", "W41"]
    }
  }
}
```

## Technical Details

### Coordinate System
- WGS84 format (EPSG:4326)
- Coordinates in decimal degrees
- Headings in degrees from true north

### Network Elements
- **Segments**: Runways, taxiways, parking positions
- **Nodes**: Intersections, gates, runway exits, parking exits
- **Gates**: Organized by terminal with precise positioning

## Development

### Data Processing Pipeline

1. **Input Data**:
   - Raw GeoJSON from OpenStreetMap
   - Airport configuration data

2. **Processing**:
   - Feature extraction and filtering
   - Network segmentation
   - Node identification
   - Gate and runway configuration

3. **Output**:
   - Network representation (LFPO.geojson)
   - Airport configuration (LFPO.json)

### Data Maintenance Guidelines

1. **Coordinate Accuracy**:
   - Verify all coordinates against official airport data
   - Maintain precision in decimal degrees

2. **Network Integrity**:
   - Ensure proper node connectivity
   - Validate segment properties
   - Keep gate information current

3. **Configuration Updates**:
   - Verify runway configurations
   - Update terminal and gate information
   - Maintain taxiway references

## Roadmap

### Phase 0: Foundation and Infrastructure (Completed)

**Airport Data Processing**
- [x] Design and implement airport data processing pipeline
- [x] Create GeoJSON network representation system
- [x] Implement coordinate system handling (WGS84)
- [x] Build segment and node identification system

**Airport Layout Implementation**
- [x] Create runway configuration management
- [x] Develop gate and parking position system
- [x] Implement heading and distance calculations

**Small Visualization**
- [X] Airport visualization (img)
- [X] Path visualization (img)

### Phase 1: Core Simulation Enhancement

**Aircraft Simulation**
- [x] Implement node and segment pathfinder
- [x] Implement pathfinder taxiway recognition
- [x] Implement realistic aircraft movement physics
- [x] Add acceleration/deceleration profiles
- [x] Include turning radius constraints
- [ ] Support different aircraft types and their specifications *(in progress)*
- [ ] Implement realistic pushback operations
- [ ] Create gate-specific pushback procedures *(might be skipped and done later)*
- [ ] Handle multiple simultaneous pushbacks
- [ ] Implement pushback coordination with taxi traffic

**Traffic Flow Management**  
- [ ] Implement conflict detection and resolution  
- [ ] Add basic ICAO rules for pushback and taxi procedures 
- [ ] Create queuing system for runway operations  *(might be skiped and done later idk)*
- [ ] Develop holding point management  *(might be skiped and done later idk)*

**Time Management**  
- [ ] Add real-time simulation clock  
- [ ] Implement time-based event scheduling  
- [ ] Support time compression/dilation for training  
- [ ] Include realistic event pre-calculation

### Phase 2: AI Development

**AI Model Development**  
- [ ] Design reinforcement learning environment with Q-value trial and error progress
- [ ] Implement reward functions for:  
  - [ ] Safety compliance  
  - [ ] Efficiency (minimal taxi time)  
  - [ ] Fuel optimization  (minimal taxi time and minimal turns given)
  - [ ] Conflict avoidance  
- [ ] Create hierarchical decision-making system
- [ ] Develop separate models for different control tasks  

**Training Pipeline**  
- [ ] Set up distributed training infrastructure  
- [ ] Implement curriculum learning  
- [ ] Create scenario generation system  
- [ ] Develop performance metrics and evaluation tools  

**Model Validation**  
- [ ] Create comprehensive test scenarios  
- [ ] Implement stress testing  
- [ ] Develop comparison metrics against human controllers  
- [ ] Set up continuous validation pipeline  

### Phase 3: Visualization

**Visualization**  
- [ ] Implement 2D/Web visualization  
- [ ] Create replay system  
- [ ] Develop customizable views

**We'll see for more...**

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

No license of any kind, do whatever the heck you want, **BUT PLEASE CREDIT !**

(Also I'm always intrested on knowing what you did with this) 