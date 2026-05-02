#!/usr/bin/env python3

import sys
import os
import heapq
from dataclasses import dataclass

from parser import Process, KrpsimParser
from config import PARALLEL_MODE, MAX_PARALLEL, TICK_MODE

@dataclass(order=True, slots=True)
class Event:
    """
    Represent a scheduled simulation event stored in the event heap.

    order=True  — auto-generates __lt__, __le__, __gt__, __ge__ by field order.
    slots=True  — replaces __dict__ with fixed-size slots, reducing memory
                  footprint since Event is instantiated once per process execution.

    Attributes:
        time: The simulation time at which the event fires.
        process_name: Name of the process this event belongs to.
    """

    time: int
    process_name: str


class KrpsimSimulator:
    """
    Simulate the execution of resource-based processes over time.

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

    def __init__(self, stocks: dict[str, int], processes: list[Process], optimize: list[str]) -> None:
        """
        Initialize the simulator with an initial state.

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
        self.running_processes = {}  # process_name -> number of instances currently running

        self.process_count = {p.name: 0 for p in processes}


        producers = {}
        for p in processes:
            for res in p.results:
                producers.setdefault(res, []).append(p)


        from collections import defaultdict
        import math

        def compute_plan(process, producers, times, stocks,
                        proc_count=None, raw_needs=None, visiting=None):

            if proc_count is None:
                proc_count = defaultdict(int)
            if raw_needs is None:
                raw_needs = defaultdict(int)
            if visiting is None:
                visiting = set()

            # 🔒 cycle guard
            if process.name in visiting:
                return proc_count, raw_needs

            visiting.add(process.name)
            proc_count[process.name] += times

            for resource, qty in process.needs.items():
                total_needed = qty * times

                # ✅ BREAK CYCLE: use available stock first
                if stocks.get(resource, 0) >= total_needed:
                    raw_needs[resource] += total_needed
                    continue

                # remaining needed after stock
                remaining = total_needed - stocks.get(resource, 0)

                # raw resource
                if resource not in producers:
                    raw_needs[resource] += remaining
                    continue

                # find producer
                producer = None
                for p in producers[resource]:
                    if resource not in p.needs or p.needs[resource] != p.results.get(resource, 0):
                        producer = p
                        break

                if producer is None:
                    continue

                produced_qty = producer.results[resource]
                required_runs = math.ceil(remaining / produced_qty)

                compute_plan(producer, producers, required_runs,
                            stocks, proc_count, raw_needs, visiting)

            visiting.remove(process.name)
            return proc_count, raw_needs
        
        for x in self.optimize_criteria:
            if x != 'time':
                opt_for = x
                
        print("opt for is: ", opt_for)
        
        final_processes = []
        for p in processes:
            res = p.results.get(opt_for, 0)
            if(res > 0):
                final_processes.append(p)
        
        # print(final_processes)
        
        # def best_coin_process(processes, opt_for):
        #     best = None
        #     best_value = float("-inf")

        #     for p in processes:
        #         coins = p.results.get(opt_for, 0)

        #         if coins > best_value:
        #             best_value = coins
        #             best = p

        #     return best
        
        # opt = best_coin_process(processes, self.optimize_criteria[-1])
        # print(opt)
        # sell_ring = next(p for p in processes if p.name == opt.name)
        # self.proc_count, self.raw_needs = compute_plan(sell_ring, producers, 1)

        # print(self.proc_count)
        # print(self.raw_needs)
        # print(stocks)
        from collections import defaultdict
        import copy

        def find_best_combination(processes, producers, stocks, opt_for):
            best_value = 0
            best_proc_count = None
            best_raw_needs = None

            def can_apply(raw_needs, stocks):
                for r, q in raw_needs.items():
                    if stocks.get(r, 0) < q:
                        return False
                return True

            def dfs(stocks, proc_count, raw_needs):
                nonlocal best_value, best_proc_count, best_raw_needs

                # current score
                value = stocks.get(opt_for, 0)

                if value > best_value:
                    best_value = value
                    best_proc_count = proc_count.copy()
                    best_raw_needs = raw_needs.copy()

                # try all processes
                for p in processes:
                    if opt_for not in p.results:
                        continue

                    # compute cost of doing it once
                    new_proc_count, needed = compute_plan(p, producers, 1, stocks)

                    # check feasibility
                    if not can_apply(needed, stocks):
                        continue

                    # 🔥 APPLY
                    new_stocks = stocks.copy()

                    # consume raw resources
                    for r, q in needed.items():
                        new_stocks[r] -= q

                    # add result
                    for r, q in p.results.items():
                        new_stocks[r] = new_stocks.get(r, 0) + q

                    # update process counts
                    updated_proc_count = proc_count.copy()
                    for k, v in new_proc_count.items():
                        updated_proc_count[k] += v

                    # update raw usage
                    updated_raw = raw_needs.copy()
                    for k, v in needed.items():
                        updated_raw[k] += v

                    # recurse
                    dfs(new_stocks, updated_proc_count, updated_raw)

            dfs(copy.deepcopy(stocks), defaultdict(int), defaultdict(int))

            return best_proc_count, best_raw_needs, best_value
        
        proc_count, raw_needs, value = find_best_combination(
            final_processes,
            producers,
            self.initial_stocks,
            opt_for
        )

        print(proc_count)
        print(raw_needs)
        print("best value:", value)
        

    def can_execute_process(self, process: Process) -> bool:
        """
        Check whether a process can be started right now.

        A process is executable if all required resources are available in
        sufficient quantities. Multiple instances of the same process can run
        in parallel as long as the stocks allow it.

        Args:
            process: The process to evaluate.

        Returns:
            True if the process can be started, False otherwise.
        """
        if PARALLEL_MODE == "concurrent":
            if self.running_processes.get(process.name, 0) >= MAX_PARALLEL:
                return False  # already at the concurrent instance cap for this process

        for resource, needed_qty in process.needs.items(): # .items() returns each key-value pair of the dict as a tuple (key, value)
            if self.current_stocks.get(resource, 0) < needed_qty: # .get returns 0 if the resource is not in stocks instead of raising a KeyError
                return False
        return True

    def consume_resources(self, process: Process) -> None:
        """
        Deduct a process's required resources from the current stock.

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
        """
        Add a process's output resources to the current stock.

        Args:
            process: The process whose results will be produced.
        """
        for resource, qty in process.results.items():
            self.current_stocks[resource] = self.current_stocks.get(resource, 0) + qty

    def start_process(self, process: Process, verbose: bool = True) -> None:
        """
        Start a process: consume its inputs, schedule its finish event, and log it.

        Args:
            process: The process to start.
        """
        self.consume_resources(process)
        self.running_processes[process.name] = self.running_processes.get(process.name, 0) + 1

        finish_time = self.current_time + process.delay
        finish_event = Event(time = finish_time,
                             process_name = process.name)
        heapq.heappush(self.events, finish_event)

        self.execution_log.append((self.current_time, process.name))
        self.process_count[process.name] += 1

        if verbose:
            print(f"{self.current_time}:{process.name}")

    def finish_process(self, process_name: str) -> None:
        """
        Complete a process: produce its outputs and mark it as no longer running.

        Args:
            process_name: Name of the process that has finished.
        """
        process = self.processes[process_name]
        self.produce_resources(process)
        self.running_processes[process_name] -= 1
        if self.running_processes[process_name] == 0:
            del self.running_processes[process_name]

    def find_executable_processes(self) -> list[Process]:
        """
        Return all processes that can be started with the current stock.

        Returns:
            A list of Process objects that pass can_execute_process.
        """
        return [p for p in self.processes.values() if self.can_execute_process(p)]

    def choose_next_process(self, executable_processes: list[Process]) -> Process | None:
        """
        Select the best process to run next using a gain-over-delay score.

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
            """
            Compute the optimization score for a single process.

            Args:
                p: The process to score.

            Returns:
                A float representing gain per time unit toward the optimize targets.
            """
            gain = sum(
                qty for res, qty in p.results.items()  # iterate over each (resource, quantity) the process produces
                if res in self.optimize_criteria        # keep only resources listed in the optimize directive
            )                                          # gain = total units produced toward optimization targets
            if 'time' in self.optimize_criteria:       # if minimizing time is a goal
                time_bonus = 1.0 / (p.delay + 1)      # faster processes get a higher bonus (+1 avoids division by zero)
                gain += time_bonus                     # add the time bonus to the raw resource gain
            if p.delay == 0:                           # instant process: avoid division by zero
                return float('inf') if gain > 0 else 0 # infinite score if it produces something useful, else 0

            return gain                    # score = gain per time unit (higher is better)

        return max(executable_processes, key=process_score)

    def process_events_at_current_time(self) -> None:
        """
        Drain and handle all events scheduled at the current simulation time.

        Pops every event from the heap whose time matches current_time
        and calls finish_process() to produce outputs and free the running slot.

        Multiple processes can finish at the same tick — this method
        handles all of them before the scheduler looks for new ones to start.
        """
        while self.events and self.events[0].time == self.current_time:
            # Pop the earliest event from the min-heap (O log n) — guaranteed to be at current_time
            # since the while condition already checked self.events[0].time == self.current_time
            event = heapq.heappop(self.events)
            self.finish_process(event.process_name)

    def has_any_executable_process(self) -> bool:
        """
        Check whether at least one process can be started right now.

        Returns:
            True if one or more processes are currently executable.
        """
        return any(self.can_execute_process(p) for p in self.processes.values())

    def advance_time(self) -> bool:
        """
        Jump the clock forward to the time of the next scheduled event.

        Returns:
            True if the clock was advanced, False if there are no pending events.
        """
        if TICK_MODE == "process_end":
            if self.events: # Checks if the heap is not empty
                self.current_time = self.events[0].time # Time of the next event
                return True
        if TICK_MODE == "+1":
            self.current_time +=1
            return True
        return False

    def simulate(self, max_time: int, verbose: bool = True) -> list[tuple[int, str]]:
        """
        Run the event-driven simulation up to max_time.

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
        iteration_safety_factor = 1000
        max_iterations = max_time * iteration_safety_factor

        while self.current_time < max_time and iteration_count < max_iterations:
            iteration_count += 1

            # 1 - Resolve all finish events scheduled at the current tick
            self.process_events_at_current_time()

            # 2 - Greedily start as many processes as possible
            started_this_tick = {}  # process_name -> times started in this scheduling round
            executable_processes = self.find_executable_processes()
            while executable_processes:
                process_to_start = self.choose_next_process(executable_processes)
                if not process_to_start:
                    break
                self.start_process(process_to_start, verbose)
                if PARALLEL_MODE == "per_tick":
                    started_this_tick[process_to_start.name] = started_this_tick.get(process_to_start.name, 0) + 1
                executable_processes = [
                    p for p in self.find_executable_processes()
                    if PARALLEL_MODE != "per_tick" or started_this_tick.get(p.name, 0) < MAX_PARALLEL
                ]

            # 3 - If nothing is running and nothing can be started, the simulation is dead
            if not self.running_processes and not self.has_any_executable_process():
                if verbose:
                    print(f"no more process doable at time {self.current_time}")
                break

            # 4 - Jump directly to the next event time instead of incrementing tick by tick
            if not self.advance_time():
                break

        # Final drain: resolve remaining events started before max_time
        # but finishing after it, to ensure correct final stock values
        while self.events:
            event = heapq.heappop(self.events)
            self.current_time = event.time
            self.finish_process(event.process_name)

        if iteration_count >= max_iterations:
            print(f"Simulation stopped after {max_iterations} iterations (infinite loop protection)")

        return self.execution_log

    def display_final_state(self) -> None:
        """
        Print the final quantity of every resource to stdout.
        """
        print("\nStock(s) :")
        for stock_name, quantity in sorted(self.current_stocks.items()):
            print(f"  {stock_name} => {quantity}")

    def display_statistics(self) -> None:
        """
        Print execution statistics including total time and per-process run counts.
        """
        print("\nStatistics:")
        print(f"Total time: {self.current_time}")
        print("Executed processes:")
        for process_name, count in self.process_count.items():
            if count > 0:
                print(f"  {process_name}: {count} times")

    def get_trace_output(self) -> str:
        """
        Serialize the execution log to the krpsim_verif trace format.

        Returns:
            A newline-separated string of 'time:process_name' entries.
        """
        return '\n'.join(f"{time}:{name}" for time, name in self.execution_log)


def main() -> None:
    """
    Entry point of the krpsim simulator.

    Parses command-line arguments, loads and validates the configuration file,
    runs the simulation within the given time delay, displays the final stock
    state, and writes the execution trace to a file for later verification.

    Usage:
        python krpsim.py <config_file_path> <delay>

    Args:
        <config_file_path>: Path to the krpsim configuration file containing
                            stock definitions, process descriptions, and the
                            optimize directive.
        <delay>:            Maximum allowed wall-clock time (in seconds) for
                            the simulation to run.

    Exits:
        1 - if the wrong number of arguments is provided.
        1 - if the configuration file cannot be parsed.
    """
    # Enforce strict argument count: exactly config file + delay
    if len(sys.argv) != 3:
        print("Usage: python krpsim.py <config_file_path> <delay>")
        sys.exit(1)

    config_file_path = sys.argv[1]
    try:
        delay = int(sys.argv[2])
    except ValueError:
        print("Error: delay must be an integer.")
        sys.exit(1)

    # Parse the configuration file into stocks, processes, and optimize targets
    parser = KrpsimParser()
    if parser.parse_file(config_file_path):
        parser.display_summary()
    else:
        print("Failed to parse the configuration file.")
        sys.exit(1)

    # Initialize the simulator with the parsed data and run it within the delay
    simulator = KrpsimSimulator(parser.stocks, parser.processes, parser.optimize)
    simulator.simulate(max_time = delay, verbose = True)

    # Print the final stock quantities after simulation ends
    simulator.display_final_state()

    # Write the execution trace to the traces folder so it can be verified later by krpsim_verif
    traces_folder = './traces'
    os.makedirs(traces_folder, exist_ok=True)

    with open(f'{traces_folder}/simulation_trace.txt', 'w') as f:
        f.write(simulator.get_trace_output())


if __name__ == "__main__":
    main()
