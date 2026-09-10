# MARINeX ML Explainability Validation (SIH26143)

This document describes the explainability validation of the **production UNet**
(`marinex-unet-v1.0.0`, `models/best_model/marinex_unet_v1.pt`) and the honest
limits of its attribution maps. For the portfolio of available methods
(Occlusion, GradCAM, attention proxy) see `docs/ML_EXPLAINABILITY.md`.

## 1. Methods on the Production Model

- **OcclusionSensitivity** (`ml/explainability/methods.py`): sliding 16x16
  patches (stride 12, fill 0.5) over the percentile-preprocessed input;
  attribution = local drop in predicted oil presence within the occluded cell.
- **GradCAM**: channel-weighted gradients on the model's decoder convolution,
  projected to input resolution.

`POST /explainability/run` exposes these via the backend; the CLI runner is
`scripts/explain_sanity.py`.

## 2. Validation Suite

`scripts/explain_sanity.py` (sample `patch_0101`) runs two **falsification**
checks so saliency is trustworthy rather than decorative (JSON output:
`reports/explainability/sanity.json`):

1. **Randomization (model-sensitivity) test**: replaces the trained weights with
   a randomly-initialized copy and re-computes attribution for the SAME input.
   Meaningful saliency must be input-driven, i.e. its energy must collapse.
   Result is `PASS` when sensitivity > 40%, otherwise `WEAK`.
2. **Perturbation (causal) test**: destroys the top-10% high-attribution region
   (Gaussian blur + dilation) and requires local confidence to drop
   meaningfully (> 0.02) - the attributed pixels must actually matter.

## 3. Results (verified)

From `reports/explainability/sanity.json` (sample `patch_0101`):

| Check | Result | Detail |
|---|---|---|
| Randomization test | **WEAK** | trained-model energy 7396.24 vs random-weights energy 47763.59 (input-sensitivity -545.8%). |
| Perturbation test | **PASS** | destroying the top-10% attribution region lowered local confidence by 0.0549 (~0.055). |

Sample meta: aggregate model confidence 0.2631; the model is **not** confident
of oil presence on this sample, and attention concentrates near
`[106.02, 159.50]` (GradCAM peak 1.0, mean 0.043).

## 4. Honest Limitations

- **WEAK randomization result**: the trained model's occlusion energy is *below*
  the random-weights baseline on this sample, which means the attribution maps
  are **not proven to be meaningfully input-driven here**. Consequently saliency
  maps for the production model **must not be over-interpreted**; the suite's
  structured explanation explicitly says *"attribution passed only partially -
  treat saliency maps with caution"*.
- The perturbation test does pass (the flagged region is causally involved), but
  that alone does not override the randomization caveat.
- Results are for a single-slice sanity sample (`patch_0101`), not a full-test
  distribution of attribution behaviors.
- The SegFormer `attention` method is a documented activation proxy, not raw
  transformer attention (see `docs/ML_EXPLAINABILITY.md`).

## 5. Artifacts

`reports/explainability/`:

- `sanity.json` - the two falsification checks + structured explanation
- `EXP-*.json` / `EXP-*_gradcam.png` / `EXP-*_occlusion.png` - provenance +
  attribution panels
- `patch_0101_panel.json` / `patch_0101_panel.png` - method panel for patch_0101

## References

- `scripts/explain_sanity.py` - validation suite
- `reports/explainability/sanity.json` - check results
- `ml/explainability/methods.py` - Occlusion / GradCAM implementations
- `docs/ML_EXPLAINABILITY.md` - methods and portfolio