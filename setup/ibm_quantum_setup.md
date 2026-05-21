# IBM Quantum Setup

## Account and API Key

Create a free account at [quantum.cloud.ibm.com](https://quantum.cloud.ibm.com) and generate an API key from the dashboard. The Open Plan gives access to real hardware including ibm_fez, ibm_marrakesh, and ibm_pittsburgh.

## Environment

```bash
conda create -n qiskit-env python=3.11
conda activate qiskit-env
pip install -r requirements.txt
```

## Saving Credentials

Run `setup/initial_setup.py` once after adding your token. Credentials are saved to `~/.qiskit/qiskit-ibm.json` and do not need to be passed explicitly in subsequent scripts.

```python
from qiskit_ibm_runtime import QiskitRuntimeService

QiskitRuntimeService.save_account(
    channel="ibm_quantum_platform",
    token="YOUR_API_TOKEN"
)
```

## Verify Connection

```bash
python setup/verification.py
```

This lists available backends with their qubit counts and current queue lengths.

## Notes

- QPU runtime is only consumed when submitting circuits, not when listing backends or loading data.
- Use `min_num_qubits=133` when selecting a backend for 60-qubit circuits to give the transpiler layout flexibility.
- The `ibm_quantum_platform` channel string is required; `ibm_quantum` is deprecated.
