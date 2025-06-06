"""
Main entry point for the vTAXI package.
"""

import argparse
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).parent
DATA_DIR = PACKAGE_ROOT / 'data'
CONFIG_DIR = PACKAGE_ROOT / 'config'

from .tools.airport_process import AirportProcessor
from .core.airport_position_assigner import AirportPositionAssigner

def process_airport_data(args):
    """Process airport layout data."""
    processor = AirportProcessor(args.geojson, args.json)
    processor.load_data()
    processor.process_layout()
    processor.export_network(args.output_network)
    processor.export_config(args.output_config)
    print(f"\nProcessed data saved to {args.output_network} and {args.output_config}")

def assign_movement(args):
    """Assign runway and gate positions for aircraft movement."""
    try:
        # Initialize the assignment system
        assigner = AirportPositionAssigner(args.airport_data)
        
        # Get assignment
        assignment = assigner.assign_positions(
            movement_type=args.type,
            config_direction=args.config,
            specific_gate=args.gate,
            specific_runway_point=args.runway_point,
            terminal_preference=args.terminal,
            exclude_gates=args.exclude_gates.split(',') if args.exclude_gates else None,
            exclude_terminals=args.exclude_terminals.split(',') if args.exclude_terminals else None
        )
        
        # Print results
        print("\nFinal Assignment:")
        print("-----------------")
        print(f"Configuration: {assignment['config']['name']}")
        print(f"{'Departure' if args.type == 'departure' else 'Arrival'} Runway: {assignment['config'][args.type]}")
        
        if assignment['gate'] and assignment['runway_point']:
            if args.type == 'departure':
                print(f"Starting Gate: {assignment['gate']['gate_id']}")
                print(f"Runway Entrance: {assignment['runway_point']}")
            else:
                print(f"Runway Exit: {assignment['runway_point']}")
                print(f"Destination Gate: {assignment['gate']['gate_id']}")
        else:
            print("\nError: Could not find suitable positions")
            
    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='vTAXI - Virtual Air Traffic Controller for Ground Operations'
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Process airport data command
    process_parser = subparsers.add_parser(
        'process',
        help='Process airport layout data'
    )
    process_parser.add_argument(
        '--geojson',
        required=True,
        help='Path to airport GeoJSON file'
    )
    process_parser.add_argument(
        '--json',
        required=True,
        help='Path to supplementary JSON file'
    )
    process_parser.add_argument(
        '--output-network',
        default=str(DATA_DIR / 'LFPO.geojson'),
        help='Output path for processed network data'
    )
    process_parser.add_argument(
        '--output-config',
        default=str(DATA_DIR / 'LFPO.json'),
        help='Output path for processed configuration'
    )
    
    # Assign movement command
    assign_parser = subparsers.add_parser(
        'assign',
        help='Assign positions for aircraft movement'
    )
    assign_parser.add_argument(
        '--type',
        choices=['arrival', 'departure'],
        required=True,
        help='Type of movement'
    )
    assign_parser.add_argument(
        '--config',
        choices=['EAST', 'WEST'],
        help='Specific runway configuration (optional)'
    )
    assign_parser.add_argument(
        '--gate',
        help='Specific gate request (optional)'
    )
    assign_parser.add_argument(
        '--runway-point',
        help='Specific runway entry/exit point (optional)'
    )
    assign_parser.add_argument(
        '--terminal',
        help='Preferred terminal (optional)'
    )
    assign_parser.add_argument(
        '--exclude-gates',
        help='Comma-separated list of gates to exclude (optional)'
    )
    assign_parser.add_argument(
        '--exclude-terminals',
        help='Comma-separated list of terminals to exclude (optional)'
    )
    assign_parser.add_argument(
        '--airport-data',
        default=str(DATA_DIR / 'LFPO.json'),
        help='Path to processed airport data'
    )
    
    args = parser.parse_args()
    
    if args.command == 'process':
        process_airport_data(args)
    elif args.command == 'assign':
        assign_movement(args)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main() 