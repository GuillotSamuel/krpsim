#!/usr/bin/env python3

import heapq
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from parser import Process, KrpsimParser

@dataclass
class Event:
    time: int
    process_name: str
    action_type: str  # 'start' or 'finish'
    
    def __lt__(self, other):
        return self.time < other.time

class KrpsimSimulator:
    def __init__(self, stocks: Dict[str, int], processes: List[Process], optimize: List[str]):
        self.initial_stocks = stocks.copy()
        self.current_stocks = stocks.copy()
        self.processes = {p.name: p for p in processes}
        self.optimize_criteria = optimize
        
        # Simulation states
        self.current_time = 0
        self.events = []  # Heap for future events
        self.execution_log = []  # (time, process_name)
        self.running_processes = set()  # Running processes

        # Statistics
        self.process_count = {p.name: 0 for p in processes}
        
    def can_execute_process(self, process: Process) -> bool:
        """Checks if a process can be executed with the current stocks"""
        if process.name in self.running_processes:
            return False
            
        for resource, needed_qty in process.needs.items():
            if self.current_stocks.get(resource, 0) < needed_qty:
                return False
        return True
    
    def consume_resources(self, process: Process):
        """Consumes the necessary resources to start a process"""
        for resource, qty in process.needs.items():
            self.current_stocks[resource] -= qty
            # Ensure negative stocks are handled
            if self.current_stocks[resource] < 0:
                raise ValueError(f"Negative stock for {resource}: {self.current_stocks[resource]}")
    
    def produce_resources(self, process: Process):
        """Produces the resources at the end of a process"""
        for resource, qty in process.results.items():
            if resource not in self.current_stocks:
                self.current_stocks[resource] = 0
            self.current_stocks[resource] += qty
    
    def start_process(self, process: Process):
        """Starts a process"""
        # Consume resources
        self.consume_resources(process)

        # Mark as running
        self.running_processes.add(process.name)

        # Schedule the end of the process
        finish_time = self.current_time + process.delay
        finish_event = Event(finish_time, process.name, 'finish')
        heapq.heappush(self.events, finish_event)

        # Log the start
        self.execution_log.append((self.current_time, process.name))
        self.process_count[process.name] += 1
        
        print(f"{self.current_time}:{process.name}")
    
    def finish_process(self, process_name: str):
        """Finishes a process"""
        process = self.processes[process_name]

        # Produce resources
        self.produce_resources(process)

        # Mark as finished
        self.running_processes.remove(process_name)
    
    def find_executable_processes(self) -> List[Process]:
        """Finds all executable processes at the current time"""
        executable = []
        for process in self.processes.values():
            if self.can_execute_process(process):
                executable.append(process)
        return executable
    
    def choose_next_process(self, executable_processes: List[Process]) -> Optional[Process]:
        """Simple strategy: choose the first executable process
        You can modify this function for different strategies"""
        if not executable_processes:
            return None

        # Strategy 1: First available
        # return executable_processes[0]

        # Strategy 2: Shortest process first
        return min(executable_processes, key=lambda p: p.delay)
    
    def process_events_at_current_time(self):
        """Processes all events at the current time"""
        while self.events and self.events[0].time == self.current_time:
            event = heapq.heappop(self.events)
            if event.action_type == 'finish':
                self.finish_process(event.process_name)
    
    def has_any_executable_process(self) -> bool:
        """Checks if there are any executable processes left"""
        return len(self.find_executable_processes()) > 0
    
    def advance_time(self):
        """Advances to the next event"""
        if self.events:
            next_event_time = self.events[0].time
            self.current_time = next_event_time
        else:
            # No future events, we can stop
            return False
        return True
    
    def simulate(self, max_time: int, verbose: bool = True):
        """Launches the main simulation"""
        if verbose:
            print(f"Nice file! {len(self.processes)} processes, {len(self.current_stocks)} stocks, {len(self.optimize_criteria)} to optimize")
            print("Evaluating .................. done.")
            print("Main walk")
        
        iteration_count = 0
        max_iterations = max_time * 100  # Protection against infinite loops

        while self.current_time < max_time and iteration_count < max_iterations:
            iteration_count += 1

            # 1. Process events at the current time
            self.process_events_at_current_time()

            # 2. Start new processes if possible
            executable_processes = self.find_executable_processes()
            while executable_processes:
                process_to_start = self.choose_next_process(executable_processes)
                if process_to_start:
                    self.start_process(process_to_start)
                    # Recalculate executable processes after each start
                    executable_processes = self.find_executable_processes()
                else:
                    break

            # 3. Advance to the next event if there's nothing more to do now
            if not self.running_processes and not self.has_any_executable_process():
                if verbose:
                    print(f"no more process doable at time {self.current_time}")
                break

            # Advance time
            if not self.advance_time():
                break

        # Process remaining events
        while self.events:
            event = heapq.heappop(self.events)
            self.current_time = event.time
            if event.action_type == 'finish':
                self.finish_process(event.process_name)
        
        if iteration_count >= max_iterations:
            print(f"Simulation stopped after {max_iterations} iterations (infinite loop protection)")

        return self.execution_log
    
    def display_final_state(self):
        """Displays the final state of the stocks"""
        print("\nStock :")
        for stock_name, quantity in sorted(self.current_stocks.items()):
            print(f"  {stock_name} => {quantity}")
    
    def display_statistics(self):
        """Displays simulation statistics"""
        print(f"\nStatistics:")
        print(f"Total time: {self.current_time}")
        print(f"Executed processes:")
        for process_name, count in self.process_count.items():
            if count > 0:
                print(f"  {process_name}: {count} fois")
    
    def get_trace_output(self) -> str:
        """Generates the output in the expected format for krpsim_verif"""
        output_lines = []
        for time, process_name in self.execution_log:
            output_lines.append(f"{time}:{process_name}")
        return '\n'.join(output_lines)
