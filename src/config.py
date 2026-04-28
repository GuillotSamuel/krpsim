# Parallel execution modes:
#   "unlimited"  — no restriction, any number of instances can run simultaneously
#   "per_tick"   — each process can be started at most MAX_PARALLEL times per scheduling round
#   "concurrent" — each process can have at most MAX_PARALLEL instances running at the same time
PARALLEL_MODE: str = "concurrent"
MAX_PARALLEL:  int = 1
# Advande time modes:
#   "+1"            — Jump the clock forward of one tick
#   "process_end"   — Jump the clock forward at the time of the first end of the current process
TICK_MODE: str = "process_end"