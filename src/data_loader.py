"""Data loading and preprocessing for the IBM PQK CAR-T cytotoxicity dataset.

Handles the unusual CSV encoding of the raw motif files, one-hot encoding of the
4-position motif sequences, label binarization, and quantum angle scaling (1 → π/2)
for ZZFeatureMap compatibility. Preprocessing logic follows the Qiskit tutorial exactly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

DEFAULT_ARGS: dict[str, Any] = {
    "file_train_data": "train_data.csv",
    "file_test_data": "test_data.csv",
    "motifs_to_use": ["motif", "motif.1", "motif.2", "motif.3"],
    "label_name": "Nalm 6 Cytotoxicity",
    "label_binarization_threshold": 0.62,
    "filter_for_spacer_motif_third_position": False,
    "allow_spacer_motif_last_position": True,
    "min_label_value": -1,
    "encoder": "one-hot",
}


def _parse_pqk_csv_line(line: str) -> list[str]:
    line = line.strip()
    if len(line) >= 2 and line[0] == '"' and line[-1] == '"':
        line = line[1:-1]
    return line.split(",")


def read_pqk_raw_csv(path: Path | str) -> pd.DataFrame:
    """Read PQK motif CSV where each row may be stored as a single quoted field."""
    path = Path(path)
    text = path.read_text(encoding="utf-8-sig")
    rows = [_parse_pqk_csv_line(line) for line in text.splitlines() if line.strip()]
    if not rows:
        raise ValueError(f"Empty CSV: {path}")
    header, body = rows[0], rows[1:]
    widths = {len(r) for r in body}
    if len(widths) != 1 or next(iter(widths)) != len(header):
        raise ValueError(f"Inconsistent row widths in {path}: {widths}, header len {len(header)}")
    return pd.DataFrame(body, columns=header).astype(
        {c: float if c == "Nalm 6 Cytotoxicity" else int for c in header}
    )


def preprocess_data(dir_root: Path | str, args: dict[str, Any] | None = None) -> tuple:
    """Tutorial-aligned preprocessing: motifs, labels {-1,+1}, integer motif ids 0..num_class-1."""
    args = {**DEFAULT_ARGS, **(args or {})}
    root = Path(dir_root)

    train_data = read_pqk_raw_csv(root / args["file_train_data"])
    test_data = read_pqk_raw_csv(root / args["file_test_data"])

    train_data[train_data == 17] = 14
    test_data[test_data == 17] = 14

    if args["filter_for_spacer_motif_third_position"]:
        train_data = train_data[(train_data["motif.2"] == 14) | (train_data["motif.2"] == 0)]
        test_data = test_data[(test_data["motif.2"] == 14) | (test_data["motif.2"] == 0)]

    cols_keep = args["motifs_to_use"] + [args["label_name"], "Cell Number"]
    train_data = train_data[cols_keep]
    test_data = test_data[cols_keep]

    if not args["allow_spacer_motif_last_position"]:
        last_motif = args["motifs_to_use"][-1]
        train_data = train_data[(train_data[last_motif] != 14) & (train_data[last_motif] != 0)]
        test_data = test_data[(test_data[last_motif] != 14) & (test_data[last_motif] != 0)]

    train_labels = np.array(train_data[args["label_name"]], dtype=float)
    test_labels = np.array(test_data[args["label_name"]], dtype=float)

    thr = args["label_binarization_threshold"]
    min_l = args["min_label_value"]
    train_labels[train_labels > thr] = 1.0
    train_labels[train_labels < 1] = float(min_l)
    test_labels[test_labels > thr] = 1.0
    test_labels[test_labels < 1] = float(min_l)

    train_data = train_data[args["motifs_to_use"]]
    test_data = test_data[args["motifs_to_use"]]

    min_class = int(np.min(np.unique(np.concatenate([train_data.values, test_data.values]))))
    max_class = int(np.max(np.unique(np.concatenate([train_data.values, test_data.values]))))
    num_class = max_class - min_class + 1
    num_motifs = len(args["motifs_to_use"])

    train_data = train_data - min_class
    test_data = test_data - min_class

    return train_data, test_data, train_labels, test_labels, num_class, num_motifs


def data_encoder(
    args: dict[str, Any],
    train_data: pd.DataFrame,
    test_data: pd.DataFrame,
    num_class: int,
    num_motifs: int,
) -> tuple[np.ndarray, np.ndarray]:
    """One-hot encode motif indices (tutorial uses np.eye)."""
    if args.get("encoder", "one-hot") != "one-hot":
        raise ValueError("Only one-hot encoder is implemented in this repo.")

    tr = np.asarray(train_data.values, dtype=int)
    te = np.asarray(test_data.values, dtype=int)
    train_oh = np.eye(num_class)[tr].reshape(tr.shape[0], tr.shape[1] * num_class)
    test_oh = np.eye(num_class)[te].reshape(te.shape[0], te.shape[1] * num_class)
    return train_oh, test_oh


def scale_one_hot_angles(train_data: np.ndarray, test_data: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Replace 1 with π/2 for ZZFeatureMap angle compatibility (tutorial)."""
    angle = np.pi / 2
    tmp = pd.DataFrame(train_data).astype("float64")
    tmp[tmp == 1] = angle
    train_scaled = tmp.values
    tmp = pd.DataFrame(test_data).astype("float64")
    tmp[tmp == 1] = angle
    test_scaled = tmp.values
    return train_scaled, test_scaled


def load_projections(dir_root: Path | str, train_name: str, test_name: str) -> tuple[np.ndarray, np.ndarray]:
    root = Path(dir_root)
    with open(root / train_name, encoding="utf-8-sig") as f:
        proj_tr = np.loadtxt(f)
    with open(root / test_name, encoding="utf-8-sig") as f:
        proj_te = np.loadtxt(f)
    if proj_tr.shape[1] != 180 or proj_te.shape[1] != 180:
        raise ValueError(f"Expected 180 projection dims, got {proj_tr.shape}, {proj_te.shape}")
    return proj_tr, proj_te


def load_pqk_bundle(
    dir_root: Path | str | None = None,
    args: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Full Track 0 bundle: scaled classical features, labels, Heron projections.

    Returns dict with keys:
      train_data, test_data, train_labels, test_labels,
      projections_train, projections_test, num_class, num_motifs, args
    """
    args = {**DEFAULT_ARGS, **(args or {})}
    if dir_root is None:
        dir_root = Path(__file__).resolve().parents[1] / "data_tutorial" / "pqk"
    dir_root = Path(dir_root)

    train_df, test_df, y_tr, y_te, num_class, num_motifs = preprocess_data(dir_root, args)
    x_tr, x_te = data_encoder(args, train_df, test_df, num_class, num_motifs)
    x_tr, x_te = scale_one_hot_angles(x_tr, x_te)
    p_tr, p_te = load_projections(
        dir_root,
        "projections_train.csv",
        "projections_test.csv",
    )
    if p_tr.shape[0] != x_tr.shape[0] or p_te.shape[0] != x_te.shape[0]:
        raise ValueError("Projection row count does not match classical features.")

    return {
        "train_data": x_tr,
        "test_data": x_te,
        "train_labels": y_tr.astype(float),
        "test_labels": y_te.astype(float),
        "projections_train": p_tr,
        "projections_test": p_te,
        "num_class": num_class,
        "num_motifs": num_motifs,
        "args": args,
    }
