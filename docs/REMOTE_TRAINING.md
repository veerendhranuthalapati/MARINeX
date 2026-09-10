# MARINeX Remote Training & Artifact Policy

Remote (GPU) provisioning scripts in `scripts/` assume the control machine (this
repo) and the GPU box talk over a URI pair. Nothing is hard-coded to a path.

## Environment variables

| Env var | Meaning | Default |
|---|---|---|
| `DATA_ROOT` | Dataset root | `data/datasets` |
| `ARTIFACT_ROOT` | Model artifact root | `models` |
| `SPLIT_PATH` | Group-aware split JSON | `data/splits/split_group_aware_v1.json` |
| `REMOTE_DATA_URI` | Dataset URI to stage on the GPU box | — |
| `REMOTE_ARTIFACT_URI` | Checkpoint URI to pull back | — |
| `MLFLOW_URI` | MLflow tracking server (optional) | — |

`ml/train.py` and `ml/evaluate.py` resolve all paths from these; configs only
carry experiment hyper-parameters.

## Scripts

```bash
bash scripts/setup_gpu.sh          # conda env + torch + requirements on GPU box
bash scripts/prepare_data_remote.sh # stage dataset from REMOTE_DATA_URI
bash scripts/train_remote.sh       # run the configured training on the GPU box
bash scripts/evaluate_model.sh     # eval + pull artifact from REMOTE_ARTIFACT_URI
```

## Artifact / checkpoint policy (REALITY CHECK)

- Model weights (`models/checkpoints/*.pt`, `models/best_model/*.pt`) are
  **gitignored** — git only tracks code, configs, and data. Checkpoints are
  provenance-tracked by filename + seed + config reference, NOT by git.
- Never commit weights exceeding the repo size budget; keep on an artifact
  registry / `REMOTE_ARTIFACT_URI` instead and record the URI in the report
  (`reports/train_result_<model>_seed<seed>.json`).
- The exact checkpoint+seed+config that produced every reported number must be
  recoverable from the report JSON and git-tagged config.

## Data provisioning

Datasets commit inside the repo (`data/datasets`, ~29 MB total) so the GPU box
only needs `DATA_ROOT` pointing at the same layout. The manifest catalog
(`python scripts/data_status.py`) reports `local`/`remote`/`missing` so a box can
fail loudly before training instead of silently training on nothing.

## MLflow

With `MLFLOW_URI` set, `ml/train.py` logs params, metrics, and artifacts to the
tracking server. Without it, training is completely offline (artifact + JSON
report only).