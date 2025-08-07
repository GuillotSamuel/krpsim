# src/krpsim_verif.py

import sys
from typing import List, Tuple, Dict
from parser import KrpsimParser, Process

class KrpsimVerifier:
    def __init__(self, config_path: str, trace_path: str):
        self.config_path = config_path
        self.trace_path = trace_path
        self.parser = KrpsimParser()
        self.processes: Dict[str, Process] = {}
        self.current_stocks: Dict[str, int] = {}
        self.trace: List[Tuple[int, str]] = []
        self.last_time = 0

    def parse(self):
        """
        Parse the config file and load stocks and processes.
        """
        if not self.parser.parse_file(self.config_path):
            raise RuntimeError("Failed to parse the configuration file.")
        self.processes = {p.name: p for p in self.parser.processes}
        self.current_stocks = self.parser.stocks.copy()

    def load_trace(self):
        """
        Load and parse the trace file containing simulation steps.
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
        """
        Check if a process can be executed with current resources.
        """
        for res, qty in process.needs.items():
            if self.current_stocks.get(res, 0) < qty:
                return False
        return True

    def consume_resources(self, process: Process):
        for res, qty in process.needs.items():
            self.current_stocks[res] -= qty

    def produce_resources(self, process: Process):
        for res, qty in process.results.items():
            self.current_stocks[res] = self.current_stocks.get(res, 0) + qty

    def verify(self):
        """
        Run the verification of the trace using current processes and stock.
        """
        print(f"\n{'-' * 20} TRACE VERIFICATION {'-' * 20}")
        for cycle_time, process_name in self.trace:
            if process_name not in self.processes:
                raise ValueError(f"Unknown process '{process_name}' at time {cycle_time}")

            if cycle_time < self.last_time:
                raise ValueError(f"Non-monotonic time: {cycle_time} after {self.last_time}")

            process = self.processes[process_name]
            self.last_time = cycle_time + process.delay

            if not self.can_execute_process(process):
                raise RuntimeError(
                    f"Process '{process_name}' cannot be executed at time {cycle_time}. "
                    f"Current stock: {self.current_stocks}"
                )

            self.consume_resources(process)
            self.produce_resources(process)

        print("✅ Trace is valid.")
        print(f"✔️  Final cycle: {self.last_time}")
        print("📦 Final stock state:")
        for res, qty in sorted(self.current_stocks.items()):
            print(f"  {res} => {qty}")
           
def main():
    if len(sys.argv) != 3:
        print("Usage: python krpsim_verif.py <config_file> <trace_file>")
        sys.exit(1)

    verifier = KrpsimVerifier(config_path=sys.argv[1], trace_path=sys.argv[2])
    verifier.parse()
    verifier.load_trace()
    verifier.verify()


if __name__ == "__main__":
    main()
