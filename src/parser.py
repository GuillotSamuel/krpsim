# src/parser.py

import re
import sys
from typing import Dict, List, Tuple, Optional

class Process:
    def __init__(self, name: str, needs: Dict[str, int], results: Dict[str, int], delay: int):
        self.name = name
        self.needs = needs
        self.results = results
        self.delay = delay
    
    def __repr__(self):
        return f"Process({self.name}, needs={self.needs}, results={self.results}, delay={self.delay})"


class KrpsimParser:
    def __init__(self):
        self.stocks = {}
        self.processes = []
        self.optimize = []
        
    def parse_file(self, file_path) -> bool:
        try:
            with open(file_path, 'r') as file:
                lines = file.readlines()
                
            for line in lines:
                line = line.strip()
                
                if not line or line.startswith('#'):
                    continue
                
                try:
                    if ':' not in line:
                        continue

                    if line.startswith('optimize:'):
                        self._parse_optimize_line(line)
                    elif '(' in line and ')' in line:
                        self._parse_process_line(line)
                    else:
                        self._parse_stock_line(line)
                        
                except Exception as e:
                    print(f"Error parsing line '{line}': {e}")
                    return False
        
            return self._validate_parsed_data()
    
        except FileNotFoundError:
            print(f"Error: File '{file_path}' not found.")
            return False
        except Exception as e:
            print(f"Error while reading the file: {e}")
            return False
        
    def _parse_optimize_line(self, line: str):
        match = re.search(r'optimize:\(([^)]+)\)', line)
        if not match:
            raise ValueError(f"Invalid optimization format: {line}")
        
        criteria_str = match.group(1)
        self.optimize = [c.strip() for c in criteria_str.split(';') if c.strip()]
        
    def _parse_process_line(self, line: str):
        pattern = r'^([^:]+):\(([^)]*)\):\(([^)]*)\):(\d+)$'
        match = re.match(pattern, line)
        
        if not match:
            raise ValueError(f"Invalid process format: {line}")
        
        name = match.group(1).strip()
        needs_str = match.group(2).strip()
        results_str = match.group(3).strip()
        delay = int(match.group(4))
        
        needs = self._parse_resource_list(needs_str)
        results = self._parse_resource_list(results_str)
        
        process = Process(name, needs, results, delay)
        self.processes.append(process)
        
    def _parse_resource_list(self, resource_str: str) -> Dict[str, int]:
        resources = {}
        
        if not resource_str:
            return resources
        
        for item in resource_str.split(';'):
            item = item.strip()
            if not item:
                continue
                
            parts = item.split(':')
            if len(parts) != 2:
                raise ValueError(f"Invalid resource format: {item}")
            
            resource_name = parts[0].strip()
            try:
                quantity = int(parts[1].strip())
                resources[resource_name] = quantity
            except ValueError:
                raise ValueError(f"Invalid quantity for {resource_name}: {parts[1]}")
        
        return resources
        
    def _parse_stock_line(self, line: str):
        parts = line.split(':')
        if len(parts) != 2:
            raise ValueError(f"Invalid stock format: {line}")
        
        stock_name = parts[0].strip()
        try:
            quantity = int(parts[1].strip())
            self.stocks[stock_name] = quantity
        except ValueError:
            raise ValueError(f"Invalid quantity for {stock_name}: {parts[1]}")
    
    def _validate_parsed_data(self) -> bool:
        if not self.stocks:
            print("No stocks defined.")
            return False
        elif not self.processes:
            print("No processes defined.")
            return False
        elif not self.optimize:
            print("No optimization defined.")
            return False
        
        all_resources = set(self.stocks.keys())
        
        for process in self.processes:
            for resource in process.needs.keys():
                all_resources.add(resource)
            for resource in process.results.keys():
                all_resources.add(resource)

        return True
    
    def display_summary(self):
        """Displays a summary of the parsed configuration""" 
               
        print(f"\n{25*'-'}PARSING{25*'-'}\n")    
        print(f"{len(self.processes)} processes, {len(self.stocks)} stocks, {len(self.optimize)} to optimize")
        
        print("\nStocks initiaux:")
        for stock, qty in self.stocks.items():
            print(f"  {stock} => {qty}")
        
        print("\nProcessus:")
        for process in self.processes:
            print(f"  {process.name}: {process.needs} -> {process.results} (délai: {process.delay})")
        
        print(f"\nOptimisation: {self.optimize}")
        
        
        
