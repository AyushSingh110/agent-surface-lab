# paper-recovery

This study asks a practical repair question: when a tool-using language-model
agent fails, which interventions actually recover the run?

The experiment records failing traces, rewinds each trace to an oracle-labeled
failure step, applies one intervention, replays forward, and scores the result
with a deterministic verifier. A no-op replay is kept as the control, so recovery
is measured against the rate at which a run would have recovered without a
repair.

## Failure Mechanisms

- **skipped-lookup**: the agent fabricates a fact that was available behind a
  tool call but never fetched.
- **tool-false-validation**: the agent feeds an operand-shaped string, such as a
  date or clock time, to a general arithmetic tool. The tool returns a non-error
  number, which falsely validates a meaningless computation.

## Scripts

- `pilot.py`: early pilot driver.
- `pilot_v2.py`: second pilot driver for the expanded task family.
- `run_recovery.py`: recovery sweep driver.
- `run_recovery_firm.py`: firmer replay sweep for selected cells.
- `run_recovery_v2.py`: updated recovery driver.

Run configuration lives in `paper-recovery/configs/`.

Raw traces and local analysis outputs are intentionally not tracked in Git.
