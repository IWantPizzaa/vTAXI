"""
Airport Position Assignment Module
Handles the assignment of runways, gates, and taxiways for aircraft movements.
Provides flexible assignment with both specific and random options for all parameters.
"""

import json
import random
from typing import Dict, List, Optional, Literal

# Type hints for configuration
ConfigDirection = Literal["EAST", "WEST"]
MovementType = Literal["arrival", "departure"]

class AirportPositionAssigner:
    """
    Assigns positions (runways, gates, entry/exit points) for aircraft movements.
    Provides flexibility to specify exact positions or use random assignments.
    """
    
    def __init__(self, processed_data_path: str):
        """
        Initialize the position assigner.
        
        Args:
            processed_data_path: Path to the processed airport data file
        """
        # Load processed data
        with open(processed_data_path, 'r') as f:
            data = json.load(f)
            self.config = data
            
        # Validate required data
        if 'runway_configurations' not in self.config:
            raise ValueError("No runway configurations found in airport data")
            
        print(f"\nLoaded runway configurations: {', '.join(self.config['runway_configurations'].keys())}")
        print(f"Loaded {self.config['gates']['total_count']} gates")
        print(f"Available runways: {', '.join(self.config['runways'].keys())}")
        
        # Store available options for easy access
        self.available_configs = list(self.config['runway_configurations'].keys())
        self.available_terminals = list(self.config['gates']['terminals'].keys())
        
    def get_config(self, direction: Optional[ConfigDirection] = None) -> Dict[str, dict]:
        """
        Get runway configuration. If direction is specified, returns that configuration,
        otherwise returns a random one.
        
        Args:
            direction: Optional direction ("EAST" or "WEST")
            
        Returns:
            Dictionary containing the selected configuration
            
        Raises:
            ValueError: If specified direction is invalid
        """
        if direction:
            if direction not in self.config['runway_configurations']:
                raise ValueError(f"Invalid configuration direction: {direction}. Valid options: {self.available_configs}")
            config = self.config['runway_configurations'][direction]
            config_name = direction
        else:
            config_name = random.choice(self.available_configs)
            config = self.config['runway_configurations'][config_name]
            
        return {
            'name': config_name,
            **config
        }
    
    def get_gate_by_id(self, gate_id: str) -> Optional[Dict]:
        """
        Find a gate by its identifier.
        
        Args:
            gate_id: Gate identifier (e.g., 'K24')
            
        Returns:
            Gate information or None if not found
        """
        terminal_id = ''.join(c for c in gate_id if not c.isdigit())
        if terminal_id in self.config['gates']['terminals']:
            terminal = self.config['gates']['terminals'][terminal_id]
            for gate in terminal['gates']:
                if gate['gate_id'] == gate_id:
                    return gate
        return None
    
    def find_runway_point(
        self,
        config: Dict[str, dict],
        is_departure: bool,
        specific_point: Optional[str] = None
    ) -> Optional[str]:
        """
        Find a runway entrance/exit point based on configuration.
        
        Args:
            config: The runway configuration to use
            is_departure: Whether this is for a departure (True) or arrival (False)
            specific_point: Request a specific point (optional)
            
        Returns:
            Selected entry/exit point identifier or None if not found
        """
        # Get the list of valid points based on movement type
        valid_points = config['entrances'] if is_departure else config['exits']
        point_type = 'entrance' if is_departure else 'exit'
        
        if specific_point:
            if specific_point in valid_points:
                print(f"Using specified runway {point_type}: {specific_point}")
                return specific_point
            else:
                print(f"Warning: Specified {point_type} {specific_point} not valid for this configuration")
                print(f"Valid options: {', '.join(valid_points)}")
                return None
        
        if not valid_points:
            print(f"No runway {point_type} points defined in configuration")
            return None
            
        # Select a random point
        selected = random.choice(valid_points)
        print(f"Selected runway {point_type}: {selected}")
        return selected
    
    def find_gate(
        self,
        specific_gate: Optional[str] = None,
        terminal_preference: Optional[str] = None,
        exclude_gates: Optional[List[str]] = None,
        exclude_terminals: Optional[List[str]] = None
    ) -> Optional[Dict]:
        """
        Find a gate (parking position) based on preferences and constraints.
        
        Args:
            specific_gate: Request a specific gate (optional)
            terminal_preference: Preferred terminal identifier (optional)
            exclude_gates: List of gate IDs to exclude (optional)
            exclude_terminals: List of terminal IDs to exclude (optional)
            
        Returns:
            Dictionary containing the selected gate or None if not found
        """
        # If specific gate requested, try to get it first
        if specific_gate:
            gate = self.get_gate_by_id(specific_gate)
            if gate:
                terminal_id = ''.join(c for c in specific_gate if not c.isdigit())
                if exclude_terminals and terminal_id in exclude_terminals:
                    print(f"Warning: Requested gate {specific_gate} is in excluded terminal {terminal_id}")
                    return None
                if exclude_gates and specific_gate in exclude_gates:
                    print(f"Warning: Requested gate {specific_gate} is in excluded gates list")
                    return None
                print(f"Using specified gate: {specific_gate}")
                return gate
            else:
                print(f"Warning: Specified gate {specific_gate} not found")
                return None
        
        exclude_gates = exclude_gates or []
        exclude_terminals = exclude_terminals or []
        available_gates = []
        
        # Helper function to filter terminals
        def is_allowed_terminal(terminal_id: str) -> bool:
            if exclude_terminals and terminal_id in exclude_terminals:
                return False
            return True
        
        # If terminal preference is given and it's not excluded, try that first
        if terminal_preference and is_allowed_terminal(terminal_preference):
            if terminal_preference in self.config['gates']['terminals']:
                terminal = self.config['gates']['terminals'][terminal_preference]
                available_gates.extend([
                    gate for gate in terminal['gates']
                    if gate['gate_id'] not in exclude_gates
                ])
                
        # If no gates found in preferred terminal or no preference given
        if not available_gates:
            for terminal_id, terminal in self.config['gates']['terminals'].items():
                if not is_allowed_terminal(terminal_id):
                    continue
                available_gates.extend([
                    gate for gate in terminal['gates']
                    if gate['gate_id'] not in exclude_gates
                ])
        
        if not available_gates:
            excluded_info = []
            if exclude_terminals:
                excluded_info.append(f"excluded terminals: {', '.join(exclude_terminals)}")
            if exclude_gates:
                excluded_info.append(f"excluded gates: {', '.join(exclude_gates)}")
            print(f"No suitable gates found" + 
                  (f" ({'; '.join(excluded_info)})" if excluded_info else ""))
            return None
            
        chosen_gate = random.choice(available_gates)
        print(f"Selected gate: {chosen_gate['gate_id']}")
        return chosen_gate
    
    def assign_positions(
        self,
        movement_type: MovementType,
        config_direction: Optional[ConfigDirection] = None,
        specific_gate: Optional[str] = None,
        specific_runway_point: Optional[str] = None,
        terminal_preference: Optional[str] = None,
        exclude_gates: Optional[List[str]] = None,
        exclude_terminals: Optional[List[str]] = None
    ) -> Dict:
        """
        Assign all positions for an aircraft movement.
        Provides complete flexibility - can specify exact positions or let the system choose randomly.
        
        Args:
            movement_type: Type of movement ('arrival' or 'departure')
            config_direction: Specific runway configuration direction (optional)
            specific_gate: Request a specific gate (optional)
            specific_runway_point: Request a specific runway entry/exit point (optional)
            terminal_preference: Preferred terminal for gate assignment (optional)
            exclude_gates: List of gate IDs to exclude from assignment (optional)
            exclude_terminals: List of terminal IDs to exclude from assignment (optional)
            
        Returns:
            Dictionary containing:
            - config: Selected runway configuration
            - movement_type: Type of movement
            - gate: Selected gate information or None
            - runway_point: Selected runway entry/exit point or None
        """
        # Get runway configuration (specific or random)
        config = self.get_config(config_direction)
        print(f"\nSelected {config['name']} configuration")
        
        # Initialize result
        result = {
            'config': config,
            'movement_type': movement_type,
            'gate': None,
            'runway_point': None
        }
        
        # Get runway reference based on movement type
        runway_ref = config['departure'] if movement_type == 'departure' else config['arrival']
        print(f"\nFinding positions for {movement_type} on runway {runway_ref}")
        
        # Find suitable positions
        gate = self.find_gate(
            specific_gate=specific_gate,
            terminal_preference=terminal_preference,
            exclude_gates=exclude_gates,
            exclude_terminals=exclude_terminals
        )
        
        runway_point = self.find_runway_point(
            config,
            movement_type == 'departure',
            specific_runway_point
        )
        
        if gate and runway_point:
            result.update({
                'gate': gate,
                'runway_point': runway_point
            })
            
        return result
        
    def get_available_options(self) -> Dict[str, List[str]]:
        """
        Get lists of all available options for configurations, terminals, etc.
        Useful for validation or UI dropdowns.
        
        Returns:
            Dictionary containing lists of available options
        """
        config_data = self.config['runway_configurations']
        
        return {
            'configurations': self.available_configs,
            'terminals': self.available_terminals,
            'runway_points': {
                'EAST': {
                    'entrances': config_data['EAST']['entrances'],
                    'exits': config_data['EAST']['exits']
                },
                'WEST': {
                    'entrances': config_data['WEST']['entrances'],
                    'exits': config_data['WEST']['exits']
                }
            }
        } 