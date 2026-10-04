"""Run every experiment of the series in dependency order and log the time each step took.

    python run_all.py              # everything (about 3-4 hours on a 12-thread laptop)
    python run_all.py data leaderboard   # selected steps

Steps write into ../artifacts; figures are made afterwards by make_figures.py. Run the timing step last and
alone: it measures speed and must not share the CPU with anything else.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = {
    "download": ["download_data.py"],
    "protocol": ["protocol.py"],
    "apples": ["export_apple_grid.py"],
    "data": ["exp_data.py"],
    "metrics": ["exp_metrics.py"],
    "linear": ["exp_linear.py"],
    "svm_folds": ["exp_svm_folds.py"],
    "leaderboard": ["exp_leaderboard.py"],
    "uncertainty": ["exp_uncertainty.py"],
    "policy": ["exp_policy.py"],
    "objectives": ["exp_objectives.py"],
    "calibration": ["exp_calibration.py"],
    "dev_studies": ["exp_dev_studies.py"],
    "summarise": ["summarise.py"],
    "widgets": ["export_widgets.py"],
    "figures": ["make_figures.py"],
    "importance": ["exp_importance.py"],
    "temporal": ["exp_temporal.py"],
    "stability": ["exp_stability.py"],
    "timing": ["exp_timing.py"],
}


def main() -> None:
    wanted = sys.argv[1:] or list(STEPS)
    log = HERE.parent / "artifacts" / "run_all.log"
    for name in wanted:
        t0 = time.perf_counter()
        print(f"== {name}", flush=True)
        rc = subprocess.call([sys.executable, *STEPS[name]], cwd=HERE)
        line = f"{name}: exit {rc} in {time.perf_counter() - t0:.0f}s"
        print(line, flush=True)
        with log.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        if rc != 0:
            sys.exit(rc)


if __name__ == "__main__":
    main()
