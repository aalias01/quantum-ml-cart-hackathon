"""SVM training pipeline: GridSearchCV over the full hyperparameter grid, test evaluation,
kernel heatmap generation, and geometric separation metrics for both classical and quantum-projected features."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.svm import SVC

from .kernels import (
    geometric_separation,
    model_complexity,
    rbf_gram,
    save_kernel_heatmap_figure,
    tutorial_param_grid,
)


def make_cv():
    return StratifiedKFold(n_splits=10)


def fit_rbf_grid(
    X: np.ndarray,
    y: np.ndarray,
    *,
    cv=None,
    n_jobs: int = -1,
    verbose: int = 1,
) -> GridSearchCV:
    cv = cv or make_cv()
    param_grid = tutorial_param_grid()
    gs = GridSearchCV(
        SVC(kernel="rbf"),
        param_grid,
        cv=cv,
        verbose=verbose,
        n_jobs=n_jobs,
        scoring="f1_weighted",
    )
    gs.fit(X, y)
    return gs


def run_track0(
    bundle: dict[str, Any],
    *,
    results_dir: Path | str | None = None,
    n_jobs: int = -1,
    verbose: int = 1,
) -> dict[str, Any]:
    """Train classical and quantum-projected SVMs, evaluate on test set, generate kernel heatmaps,
    and compute geometric separation and model complexity metrics.

    Writes results/metrics.json and results/figures/kernel_heatmaps.png when results_dir is set.
    """
    results_dir = Path(results_dir or Path(__file__).resolve().parents[1] / "results")
    fig_dir = results_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    X_tr, X_te = bundle["train_data"], bundle["test_data"]
    P_tr, P_te = bundle["projections_train"], bundle["projections_test"]
    y_tr, y_te = bundle["train_labels"], bundle["test_labels"]

    grid_c = fit_rbf_grid(X_tr, y_tr, n_jobs=n_jobs, verbose=verbose)
    grid_q = fit_rbf_grid(P_tr, y_tr, n_jobs=n_jobs, verbose=verbose)

    best_c = grid_c.best_estimator_
    best_q = grid_q.best_estimator_

    pred_c_te = best_c.predict(X_te)
    pred_q_te = best_q.predict(P_te)

    metrics = {
        "classical": {
            "cv_f1_weighted": float(grid_c.best_score_),
            "test_accuracy": float(accuracy_score(y_te, pred_c_te)),
            "test_f1_weighted": float(f1_score(y_te, pred_c_te, average="weighted")),
            "best_params": grid_c.best_params_,
        },
        "quantum": {
            "cv_f1_weighted": float(grid_q.best_score_),
            "test_accuracy": float(accuracy_score(y_te, pred_q_te)),
            "test_f1_weighted": float(f1_score(y_te, pred_q_te, average="weighted")),
            "best_params": grid_q.best_params_,
        },
        "n_train": int(X_tr.shape[0]),
        "n_test": int(X_te.shape[0]),
    }

    gc = grid_c.best_params_["gamma"]
    gq = grid_q.best_params_["gamma"]
    K_c = rbf_gram(X_tr, gc)
    K_q = rbf_gram(P_tr, gq)

    save_kernel_heatmap_figure(K_c, K_q, y_tr, fig_dir / "kernel_heatmaps.png")

    C_c = float(grid_c.best_params_["C"])
    g_cq = geometric_separation(K_c, K_q, gc, gq, C_c)
    sqrt_n = float(np.sqrt(len(X_tr)))
    l_c = 1.0 / C_c
    l_q = 1.0 / float(grid_q.best_params_["C"])

    pred_c_tr = best_c.predict(X_tr)
    pred_q_tr = best_q.predict(P_tr)
    s_c = model_complexity(K_c, l_c, pred_c_tr, len(X_tr))
    s_q = model_complexity(K_q, l_q, pred_q_tr, len(P_tr))

    metrics["geometry"] = {
        "g_cq": g_cq,
        "sqrt_N": sqrt_n,
        "g_cq_over_sqrt_N": g_cq / sqrt_n,
        "s_c": s_c,
        "s_q": s_q,
    }

    out_json = results_dir / "metrics.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    metrics["_artifacts"] = {
        "metrics_json": str(out_json),
        "kernel_heatmap": str(fig_dir / "kernel_heatmaps.png"),
    }
    return metrics
