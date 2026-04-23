# krpsim

A resource-process simulator written in Python. Given a configuration file describing initial stocks, a set of processes (each consuming and producing resources over a fixed delay), and an optimization target, `krpsim` schedules and runs processes as efficiently as possible to maximize the target within a given time budget.

A companion verifier (`krpsim_verif`) replays a recorded trace against the same configuration to confirm that every step was legal.

---

## Project structure

```
krpsim/
├── src/
│   ├── krpsim.py        # Simulator entry point
│   ├── krpsim_verif.py  # Trace verifier
│   └── parser.py        # Configuration file parser
├── resources/           # Provided example configurations
├── examples/            # Additional example configurations
├── traces/              # Simulation output traces (auto-created)
└── requirements.txt
```

---

## Setup

Python 3.10+ is required. No third-party libraries are needed — only the standard library.

### Create and activate a virtual environment

```bash
python3 -m venv env
source env/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

> `requirements.txt` is currently empty; this step is a no-op but good practice.

---

## Configuration file format

A configuration file has three sections, in any order. Lines starting with `#` are comments.

### Stocks

Define an initial quantity for each resource:

```
euro:10
materiel:0
```

### Processes

Each process has a name, a list of consumed resources, a list of produced resources, and a duration (in time units):

```
name:(need1:qty1;need2:qty2):(result1:qty1;result2:qty2):delay
```

Example:

```
achat_materiel:(euro:8):(materiel:1):10
realisation_produit:(materiel:1):(produit:1):30
livraison:(produit:1):(client_content:1):20
```

### Optimization target

List the resources to maximize (or `time` to minimize total duration):

```
optimize:(time;client_content)
```

---

## Running the simulator

From the `src/` directory:

```bash
python3 krpsim.py <config_file> <max_time>
```

| Argument | Description |
|---|---|
| `config_file` | Path to the `.txt` configuration file |
| `max_time` | Maximum number of time units the simulation may run |

### Examples

```bash
# Simple demo
python3 krpsim.py ../resources/simple 100

# IKEA shelf assembly
python3 krpsim.py ../resources/ikea 100

# Apple pie bakery
python3 krpsim.py ../resources/pomme 10000

# Recess activities
python3 krpsim.py ../resources/recre 220

# Steak cooking
python3 krpsim.py ../resources/steak 50
```

The simulator prints each scheduled process as `time:process_name` and writes the full trace to `traces/simulation_trace.txt`.

---

## Verifying a trace

After a simulation, you can verify that the produced trace is valid:

```bash
python3 krpsim_verif.py <config_file> <trace_file>
```

### Example

```bash
python3 krpsim_verif.py ../resources/recre ../traces/simulation_trace.txt
```

The verifier replays every step in the trace, checks that resources were available at execution time, and prints the final stock state. It exits with an error if any step is invalid.

---

## How the scheduler works

The simulator uses an **event-driven loop** backed by a min-heap:

1. At each time step, all events whose deadline has been reached are processed (resources are produced).
2. All processes that can currently be started are scored and the best one is launched (resources consumed, finish event pushed onto the heap).
3. This repeats until no process can be started and no event is pending, or `max_time` is reached.

**Scoring** — each candidate process is ranked by:

```
score = gain / delay
```

where `gain` is the total quantity of optimized resources produced by that process. Processes producing no optimized resources are deprioritized; processes with `delay = 0` that produce optimized resources are always preferred.
