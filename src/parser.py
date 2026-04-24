# src/parser.py

import re


class Process:
    """
    Represent a single production process with its resource requirements and output.

    Attributes:
        name: Unique identifier for the process.
        needs: Resources consumed when the process starts, keyed by resource name.
        results: Resources produced when the process finishes, keyed by resource name.
        delay: Duration of the process in time units.
    """

    # Fix the set of attributes to reduce memory footprint.
    # Prevents dynamic attribute creation on instances.
    __slots__ = ('name', 'needs', 'results', 'delay')

    def __init__(self, name: str, needs: dict[str, int], results: dict[str, int], delay: int) -> None:
        """
        Initialize a process with its resource requirements and production.

        Args:
            name: Unique identifier for the process.
            needs: Mapping of resource names to quantities consumed on start.
            results: Mapping of resource names to quantities produced on finish.
            delay: Number of time units the process takes to complete.
        """
        self.name = name
        self.needs = needs
        self.results = results
        self.delay = delay

    def __repr__(self) -> str:
        """
        Return a human-readable string representation of the process.

        Returns:
            A string showing the process name, needs, results, and delay.
        """
        return f"Process({self.name}, needs={self.needs}, results={self.results}, delay={self.delay})"


class KrpsimParser:
    """
    Parse a krpsim configuration file into stocks, processes, and optimize criteria.

    Attributes:
        stocks: Initial resource quantities parsed from the file.
        processes: List of Process objects parsed from the file.
        optimize: List of resource names (or 'time') to optimize.
    """

    def __init__(self) -> None:
        """
        Initialize the parser with empty stocks, processes, and optimize lists.
        """
        self.stocks: dict[str, int] = {}
        self.processes: list[Process] = []
        self.optimize: list[str] = []

    def parse_file(self, file_path: str) -> bool:
        """
        Parse a krpsim configuration file and populate stocks, processes, and optimize.

        The file may contain stock definitions (name:quantity), process definitions
        (name:(needs):(results):delay), and an optimize directive.
        Lines starting with '#' and empty lines are ignored.

        Args:
            file_path: Path to the krpsim configuration file to parse.

        Returns:
            True  - file was read, every line parsed, and data passed validation.
            False - file not found, unreadable, malformed line, or validation failure.
        """
        try:
            with open(file_path, 'r') as file:
                for line in file:
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
        except (OSError, UnicodeDecodeError) as e:
            print(f"Error while reading the file: {e}")
            return False

    def _parse_optimize_line(self, line: str) -> None:
        """
        Parse an optimize directive and store the list of target resources.

        Expected format: optimize:(resource1;resource2;...)

        Args:
            line: The raw line containing the optimize directive.

        Raises:
            ValueError: If the line does not match the expected format.
        """
        match = re.search(r'optimize:\(([^)]+)\)', line)
        if not match:
            raise ValueError(f"Invalid optimization format: {line}")

        criteria_str = match.group(1)
        self.optimize = [c.strip() for c in criteria_str.split(';') if c.strip()]

    def _parse_process_line(self, line: str) -> None:
        """
        Parse a process definition line and append a Process object to the list.

        Expected format: name:(need1:qty1;need2:qty2):(result1:qty1;result2:qty2):delay

        Args:
            line: The raw line containing the process definition.

        Raises:
            ValueError: If the line does not match the expected format.
        """
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

    @staticmethod
    def _parse_resource_list(resource_str: str) -> dict[str, int]:
        """Parse a semicolon-separated list of resource:quantity pairs.

        Args:
            resource_str: A string of the form "res1:qty1;res2:qty2".

        Returns:
            A dictionary mapping resource names to their integer quantities.

        Raises:
            ValueError: If any pair has an invalid format or a non-integer quantity.
        """
        resources: dict[str, int] = {}

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
            except ValueError as e:
                raise ValueError(f"Invalid quantity for {resource_name}: {parts[1]}") from e

        return resources

    def _parse_stock_line(self, line: str) -> None:
        """
        Parse a stock definition line and store the initial quantity.

        Expected format: name:quantity

        Args:
            line: The raw line containing the stock definition.

        Raises:
            ValueError: If the line does not match the expected format or
                the quantity is not an integer.
        """
        parts = line.split(':')
        if len(parts) != 2:
            raise ValueError(f"Invalid stock format: {line}")

        stock_name = parts[0].strip()
        try:
            quantity = int(parts[1].strip())
            self.stocks[stock_name] = quantity
        except ValueError as e:
            raise ValueError(f"Invalid quantity for {stock_name}: {parts[1]}") from e

    def _validate_parsed_data(self) -> bool:
        """
        Validate that all required sections were found in the configuration.

        Checks that at least one stock, one process, and one optimize criterion
        were parsed.

        Returns:
            True if the configuration is complete, False otherwise.
        """
        if not self.stocks:
            print("No stocks defined.")
            return False
        if not self.processes:
            print("No processes defined.")
            return False
        if not self.optimize:
            print("No optimization defined.")
            return False

        return True

    def display_summary(self) -> None:
        """
        Print a formatted summary of the parsed configuration to stdout.

        Displays a separator header, the counts of processes/stocks/optimize
        criteria, then lists each initial stock with its quantity, each process
        with its needs, results and delay, and finally the optimization targets.

        Expected output format:
            -------------------------PARSING-------------------------
            3 processes, 4 stocks, 1 to optimize

            Initial Stocks:
            euro => 10

            Process:
            buy: {'euro': 8} -> {'material': 1} (delay: 10)

            Optimization: ['time', 'happy_client']
        """
        separator_width = 25
        print(f"\n{separator_width*'-'}PARSING{separator_width*'-'}\n")
        print(f"{len(self.processes)} processes, {len(self.stocks)} stocks, {len(self.optimize)} to optimize")

        print("\nInitial Stocks:")
        for stock, qty in self.stocks.items():
            print(f"  {stock} => {qty}")

        print("\nProcess:")
        for process in self.processes:
            print(f"  {process.name}: {process.needs} -> {process.results} (delay: {process.delay})")

        print(f"\nOptimization: {self.optimize}")
