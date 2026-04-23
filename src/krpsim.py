#!/usr/bin/env python3

import sys
import os
import heapq
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from parser import Process, KrpsimParser

@dataclass
class Event:
    """Represent a scheduled simulation event stored in the event heap.

    Attributes:
        time: The simulation time at which the event fires.
        process_name: Name of the process this event belongs to.
        action_type: Either 'start' or 'finish' depending on the event kind.
    """

    time: int
    process_name: str
    action_type: str

    def __lt__(self, other: "Event") -> bool:
        """Compare events by time for min-heap ordering.

        Args:
            other: Another Event instance to compare against.

        Returns:
            True if this event occurs before the other event.
        """
        return self.time < other.time


class KrpsimSimulator:
    """Simulate the execution of resource-based processes over time.

    The simulator runs an event-driven loop: at each time step it resolves
    finished processes, greedily starts the best-scoring available process,
    and advances the clock to the next scheduled event.

    Attributes:
        initial_stocks: Snapshot of resource quantities at simulation start.
        current_stocks: Resource quantities updated throughout the simulation.
        processes: All known processes indexed by name.
        optimize_criteria: Resource names (or 'time') used to score processes.
        current_time: Current simulation clock value.
        events: Min-heap of pending Events ordered by time.
        execution_log: Ordered list of (start_time, process_name) entries.
        running_processes: Names of processes currently in flight.
        process_count: Number of times each process has been started.
    """

    def __init__(self, stocks: Dict[str, int], processes: List[Process], optimize: List[str]) -> None:
        """Initialize the simulator with an initial state.

        Args:
            stocks: Initial resource quantities keyed by resource name.
            processes: List of all available processes.
            optimize: List of resource names (or 'time') to maximize.
        """
        self.initial_stocks = stocks.copy()
        self.current_stocks = stocks.copy()
        self.processes = {p.name: p for p in processes}
        self.optimize_criteria = optimize

        self.current_time = 0
        self.events = []
        self.execution_log = []
        self.running_processes = set()

        self.process_count = {p.name: 0 for p in processes}

    def can_execute_process(self, process: Process) -> bool:
        """Check whether a process can be started right now.

        A process is executable if it is not already running and all required
        resources are available in sufficient quantities.

        Args:
            process: The process to evaluate.

        Returns:
            True if the process can be started, False otherwise.
        """
        if process.name in self.running_processes:
            return False

        for resource, needed_qty in process.needs.items():
            if self.current_stocks.get(resource, 0) < needed_qty:
                return False
        return True

    def consume_resources(self, process: Process) -> None:
        """Deduct a process's required resources from the current stock.

        Args:
            process: The process whose needs will be consumed.

        Raises:
            ValueError: If consuming resources would result in a negative stock,
                which indicates a logic error in the scheduling.
        """
        for resource, qty in process.needs.items():
            self.current_stocks[resource] -= qty
            if self.current_stocks[resource] < 0:
                raise ValueError(f"Negative stock for {resource}: {self.current_stocks[resource]}")

    def produce_resources(self, process: Process) -> None:
        """Add a process's output resources to the current stock.

        Args:
            process: The process whose results will be produced.
        """
        for resource, qty in process.results.items():
            if resource not in self.current_stocks:
                self.current_stocks[resource] = 0
            self.current_stocks[resource] += qty

    def start_process(self, process: Process) -> None:
        """Start a process: consume its inputs, schedule its finish event, and log it.

        Args:
            process: The process to start.
        """
        self.consume_resources(process)
        self.running_processes.add(process.name)

        finish_time = self.current_time + process.delay
        finish_event = Event(finish_time, process.name, 'finish')
        heapq.heappush(self.events, finish_event)

        self.execution_log.append((self.current_time, process.name))
        self.process_count[process.name] += 1

        print(f"{self.current_time}:{process.name}")

    def finish_process(self, process_name: str) -> None:
        """Complete a process: produce its outputs and mark it as no longer running.

        Args:
            process_name: Name of the process that has finished.
        """
        process = self.processes[process_name]
        self.produce_resources(process)
        self.running_processes.remove(process_name)

    def find_executable_processes(self) -> List[Process]:
        """Return all processes that can be started with the current stock.

        Returns:
            A list of Process objects that pass can_execute_process.
        """
        executable = []
        for process in self.processes.values():
            if self.can_execute_process(process):
                executable.append(process)
        return executable

    def choose_next_process(self, executable_processes: List[Process]) -> Optional[Process]:
        """Select the best process to run next using a gain-over-delay score.

        Each process is scored by the total quantity of optimized resources it
        produces divided by its delay. Processes with delay 0 that produce
        optimized resources receive an infinite score and are always preferred.

        Args:
            executable_processes: List of processes eligible for execution.

        Returns:
            The process with the highest score, or None if the list is empty.
        """
        if not executable_processes:
            return None

        def process_score(p: Process) -> float:
            """Compute the optimization score for a single process.

            Args:
                p: The process to score.

            Returns:
                A float representing gain per time unit toward the optimize targets.
            """
            gain = sum(
                qty for res, qty in p.results.items()
                if res in self.optimize_criteria
            )
            if p.delay == 0:
                return float('inf') if gain > 0 else 0

            return gain / p.delay

        return max(executable_processes, key=process_score)

    def process_events_at_current_time(self) -> None:
        """Drain and handle all finish events scheduled at the current time step."""
        while self.events and self.events[0].time == self.current_time:
            event = heapq.heappop(self.events)
            if event.action_type == 'finish':
                self.finish_process(event.process_name)

    def has_any_executable_process(self) -> bool:
        """Check whether at least one process can be started right now.

        Returns:
            True if one or more processes are currently executable.
        """
        return len(self.find_executable_processes()) > 0

    def advance_time(self) -> bool:
        """Jump the clock forward to the time of the next scheduled event.

        Returns:
            True if the clock was advanced, False if there are no pending events.
        """
        if self.events:
            self.current_time = self.events[0].time
            return True
        return False

    def simulate(self, max_time: int, verbose: bool = True) -> List[Tuple[int, str]]:
        """Run the event-driven simulation up to max_time.

        At each time step the simulator:
          1. Resolves all finish events at the current time.
          2. Greedily starts the highest-scoring executable process until none remain.
          3. Advances the clock to the next pending event.

        The loop ends when no processes are running, none can be started, or
        max_time is reached.

        Args:
            max_time: The simulation stops when current_time reaches this value.
            verbose: If True, prints a header and an end-of-simulation message.

        Returns:
            The execution log as a list of (start_time, process_name) tuples.
        """
        if verbose:
            print(f"\n{25*'-'}SIMULATION{25*'-'}\n")

        iteration_count = 0
        max_iterations = max_time * 100

        while self.current_time < max_time and iteration_count < max_iterations:
            iteration_count += 1

            self.process_events_at_current_time()

            executable_processes = self.find_executable_processes()
            while executable_processes:
                process_to_start = self.choose_next_process(executable_processes)
                if process_to_start:
                    self.start_process(process_to_start)
                    executable_processes = self.find_executable_processes()
                else:
                    break

            if not self.running_processes and not self.has_any_executable_process():
                if verbose:
                    print(f"no more process doable at time {self.current_time}")
                break

            if not self.advance_time():
                break

        while self.events:
            event = heapq.heappop(self.events)
            self.current_time = event.time
            if event.action_type == 'finish':
                self.finish_process(event.process_name)

        if iteration_count >= max_iterations:
            print(f"Simulation stopped after {max_iterations} iterations (infinite loop protection)")

        return self.execution_log

    def display_final_state(self) -> None:
        """Print the final quantity of every resource to stdout."""
        print("\nStock :")
        for stock_name, quantity in sorted(self.current_stocks.items()):
            print(f"  {stock_name} => {quantity}")

    def display_statistics(self) -> None:
        """Print execution statistics including total time and per-process run counts."""
        print(f"\nStatistics:")
        print(f"Total time: {self.current_time}")
        print(f"Executed processes:")
        for process_name, count in self.process_count.items():
            if count > 0:
                print(f"  {process_name}: {count} times")

    def get_trace_output(self) -> str:
        """Serialize the execution log to the krpsim_verif trace format.

        Returns:
            A newline-separated string of 'time:process_name' entries.
        """
        output_lines = []
        for time, process_name in self.execution_log:
            output_lines.append(f"{time}:{process_name}")
        return '\n'.join(output_lines)

def main() -> None:
    """Entry point: parse arguments, run the simulation, and write the trace file."""
    if len(sys.argv) != 3:
        print("Usage: python krpsim.py <config_file_path> <delay>")
        sys.exit(1)

    config_file_path = sys.argv[1]
    delay = int(sys.argv[2])

    parser = KrpsimParser()

    if parser.parse_file(config_file_path):
        parser.display_summary()
    else:
        print("Failed to parse the configuration file.")
        sys.exit(1)

    simulator = KrpsimSimulator(parser.stocks, parser.processes, parser.optimize)
    execution_log = simulator.simulate(delay)

    simulator.display_final_state()

    traces_folder = '../traces'
    if not os.path.exists(traces_folder):
        os.makedirs(traces_folder)

    with open(f'{traces_folder}/simulation_trace.txt', 'w') as f:
        f.write(simulator.get_trace_output())


if __name__ == "__main__":
    main()
