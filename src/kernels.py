"""Kernel utilities: RBF Gram matrices, heatmap visualization, and the geometric separation
and model complexity metrics from Huang et al. (2021) used to assess quantum advantage."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.linalg import inv, sqrtm
from sklearn.metrics.pairwise import rbf_kernel


def tutorial_param_grid() -> dict:
    """SVM hyperparameter grid matching the IBM Qiskit PQK tutorial (6622 C × gamma combinations)."""
    C_range = [0.001, 0.005, 0.007]
    C_range += [x * 0.01 for x in range(1, 11)]
    C_range += [x * 0.25 for x in range(1, 60)]
    C_range += [20, 50, 100, 200, 500, 700, 1000, 1100, 1200, 1300, 1400, 1500, 1700, 2000]

    gamma_range = ["auto", "scale", 0.001, 0.005, 0.007]
    gamma_range += [x * 0.01 for x in range(1, 11)]
    gamma_range += [x * 0.25 for x in range(1, 60)]
    gamma_range += [20, 50, 100]

    return dict(C=C_range, gamma=gamma_range)


def resolve_rbf_gamma(X: np.ndarray, gamma) -> float | None:
    """Resolve SVC-style gamma values for sklearn.metrics.pairwise.rbf_kernel."""
    if gamma == "auto":
        return 1.0 / X.shape[1]
    if gamma == "scale":
        return 1.0 / (X.shape[1] * X.var())
    return gamma


def rbf_gram(X: np.ndarray, gamma) -> np.ndarray:
    X = np.asarray(X)
    return rbf_kernel(X, X, gamma=resolve_rbf_gamma(X, gamma))


def plot_kernel_heatmap(K: np.ndarray, labels: np.ndarray, title: str, ax) -> None:
    import seaborn as sns

    order = np.argsort(labels)
    K_sorted = K[np.ix_(order, order)]
    sns.heatmap(
        K_sorted,
        ax=ax,
        cmap="viridis",
        vmin=0,
        vmax=1,
        xticklabels=False,
        yticklabels=False,
    )
    ax.set_title(title)
    boundary = int(np.searchsorted(labels[order], 1, side="left"))
    ax.axhline(y=boundary, color="red", linewidth=1.5, linestyle="--")
    ax.axvline(x=boundary, color="red", linewidth=1.5, linestyle="--")


def save_kernel_heatmap_figure(
    K_c: np.ndarray,
    K_q: np.ndarray,
    train_labels: np.ndarray,
    out_path: Path | str,
) -> None:
    import matplotlib.pyplot as plt

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    plot_kernel_heatmap(K_c, train_labels, "Classical RBF Kernel", axes[0])
    plot_kernel_heatmap(K_q, train_labels, "Quantum-Projected RBF Kernel", axes[1])
    plt.suptitle("Kernel Structure: Classical vs. Quantum-Projected", fontsize=14, fontweight="bold")
    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def geometric_separation(
    K_c: np.ndarray,
    K_q: np.ndarray,
    gamma_c,
    gamma_q,
    C_c: float,
) -> float:
    """Geometric separation g_cq (Huang et al. 2021, eq. F19).

    Measures how different the quantum and classical kernel spaces are relative to
    the training set size. Quantum advantage is predicted when g_cq ≈ sqrt(N).
    """
    l_c = 1.0 / C_c
    K_c_sqrt = sqrtm(K_c)
    K_q_sqrt = sqrtm(K_q)
    K_c_inv = inv(K_c + l_c * np.eye(K_c.shape[0]))
    K_mult = K_q_sqrt @ K_c_sqrt @ K_c_inv @ K_c_inv @ K_c_sqrt @ K_q_sqrt
    return float(np.sqrt(np.linalg.norm(K_mult, ord=np.inf)))


def model_complexity(K: np.ndarray, l: float, y_pred: np.ndarray, N: int) -> float:
    """Model complexity s_K(N) from Huang et al. (2021), eq. M1."""
    pred_matrix = np.outer(y_pred, y_pred)
    K_inv = inv(K + l * np.eye(K.shape[0]))
    first_sum = np.sum((K_inv @ K_inv) * pred_matrix)
    first_term = l * np.sqrt(first_sum / N)
    second_sum = np.sum((K_inv @ K @ K_inv) * pred_matrix)
    second_term = np.sqrt(second_sum / N)
    return float(first_term + second_term)
