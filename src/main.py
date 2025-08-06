# src/main.py
import os
import sys
from parser import KrpsimParser
from krpsim import KrpsimSimulator

def main():
    # Check command line arguments
    if len(sys.argv) != 3:
        print("Usage: python main.py <config_file_path> <delay>")
        sys.exit(1)

    config_file_path = sys.argv[1]
    delay = int(sys.argv[2])
    
    # Parsing the configuration file
    parser = KrpsimParser()

    if parser.parse_file(config_file_path):
        parser.display_summary()
    else:
        print("Failed to parse the configuration file.")
        
    # Krpsim simulator
    simulator = KrpsimSimulator(parser.stocks, parser.processes, parser.optimize)
    execution_log = simulator.simulate(delay)
    
    simulator.display_final_state()
    
    # check traces folder and create if not exists
    traces_folder = '../traces'
    if not os.path.exists(traces_folder):
        os.makedirs(traces_folder)
    
    with open(f'{traces_folder}/simulation_trace.txt', 'w') as f:
        f.write(simulator.get_trace_output())  


if __name__ == "__main__":
    main()