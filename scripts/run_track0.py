#!/usr/bin/env python3
"""Command-line entrypoint for the Track 0 baseline: loads the CAR-T dataset, trains
classical and quantum-projected SVMs via GridSearchCV, generates kernel heatmaps, and
writes all metrics to results/metrics.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_loader import load_pqk_bundle
from src.experiments import run_track0


def main() -> None:
    data_dir = ROOT / "data_tutorial" / "pqk"
    bundle = load_pqk_bundle(data_dir)
    metrics = run_track0(bundle, results_dir=ROOT / "results", n_jobs=-1, verbose=1)
    out = {k: v for k, v in metrics.items() if k != "_artifacts"}
    out["_artifacts"] = metrics.get("_artifacts", {})
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
