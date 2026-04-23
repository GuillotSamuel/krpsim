# src/krpsim_verif.py

import sys
from typing import List, Tuple, Dict
from parser import KrpsimParser, Process

class KrpsimVerifier:
    """Verify a simulation trace against a krpsim configuration file.

    Replays every (time, process) entry in the trace, checks resource
    availability at each step, and reports the final stock state.

    Attributes:
        config_path: Path to the krpsim configuration file.
        trace_path: Path to the trace file produced by the simulator.
        parser: KrpsimParser instance used to load the configuration.
        processes: All known processes indexed by name.
        current_stocks: Resource quantities updated as the trace is replayed.
        trace: Ordered list of (start_time, process_name) loaded from the trace file.
        last_start_time: Start time of the most recently verified trace entry,
            used to enforce monotonic ordering.
    """

    def __init__(self, config_path: str, trace_path: str) -> None:
        """Initialize the verifier with paths to the configuration and trace files.

        Args:
            config_path: Path to the krpsim configuration file.
            trace_path: Path to the trace file produced by the simulator.
        """
        self.config_path = config_path
        self.trace_path = trace_path
        self.parser = KrpsimParser()
        self.processes: Dict[str, Process] = {}
        self.current_stocks: Dict[str, int] = {}
        self.trace: List[Tuple[int, str]] = []
        self.last_start_time = 0

    def parse(self) -> None:
        """Parse the configuration file and load stocks and processes.

        Raises:
            RuntimeError: If the configuration file cannot be parsed.
        """
        if not self.parser.parse_file(self.config_path):
            raise RuntimeError("Failed to parse the configuration file.")
        self.processes = {p.name: p for p in self.parser.processes}
        self.current_stocks = self.parser.stocks.copy()

    def load_trace(self) -> None:
        """Load and parse the trace file into an ordered list of timed events.

        Each non-empty line must follow the format 'time:process_name'.
        Lines that do not contain ':' are silently skipped.
        """
        self.trace = []
        with open(self.trace_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or ":" not in line:
                    continue
                time_str, process_name = line.split(":", 1)
                self.trace.append((int(time_str), process_name))

    def can_execute_process(self, process: Process) -> bool:
        """Check whether a process can be executed with the current stock.

        Args:
            process: The process to evaluate.

        Returns:
            True if all required resources are available in sufficient quantities.
        """
        for res, qty in process.needs.items():
            if self.current_stocks.get(res, 0) < qty:
                return False
        return True

    def consume_resources(self, process: Process) -> None:
        """Deduct a process's required resources from the current stock.

        Args:
            process: The process whose inputs will be consumed.
        """
        for res, qty in process.needs.items():
            self.current_stocks[res] -= qty

    def produce_resources(self, process: Process) -> None:
        """Add a process's output resources to the current stock.

        Args:
            process: The process whose outputs will be produced.
        """
        for res, qty in process.results.items():
            self.current_stocks[res] = self.current_stocks.get(res, 0) + qty

    def verify(self) -> None:
        """Replay the trace and validate every step against the configuration.

        For each entry in the trace the verifier checks:
          - The process name exists in the configuration.
          - Time is monotonically non-decreasing.
          - All required resources are available before the process starts.

        Raises:
            ValueError: If an unknown process is referenced or time goes backwards.
            RuntimeError: If a process cannot be executed due to insufficient resources.
        """
        print(f"\n{'-' * 20} TRACE VERIFICATION {'-' * 20}")
        last_finish_time = 0
        for cycle_time, process_name in self.trace:
            if process_name not in self.processes:
                raise ValueError(f"Unknown process '{process_name}' at time {cycle_time}")

            if cycle_time < self.last_start_time:
                raise ValueError(f"Non-monotonic time: {cycle_time} after {self.last_start_time}")

            process = self.processes[process_name]
            self.last_start_time = cycle_time
            last_finish_time = max(last_finish_time, cycle_time + process.delay)

            if not self.can_execute_process(process):
                raise RuntimeError(
                    f"Process '{process_name}' cannot be executed at time {cycle_time}. "
                    f"Current stock: {self.current_stocks}"
                )

            self.consume_resources(process)
            self.produce_resources(process)

        print("Trace is valid.")
        print(f"\nFinal cycle: {last_finish_time}")
        print("\nFinal stock state:")
        for res, qty in sorted(self.current_stocks.items()):
            print(f"  {res} => {qty}")

def main() -> None:
    """Entry point: parse arguments, load the trace, and run verification."""
    if len(sys.argv) != 3:
        print("Usage: python krpsim_verif.py <config_file> <trace_file>")
        sys.exit(1)

    verifier = KrpsimVerifier(config_path=sys.argv[1], trace_path=sys.argv[2])
    verifier.parse()
    verifier.load_trace()
    verifier.verify()


if __name__ == "__main__":
    main()
