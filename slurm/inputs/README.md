# Regeneration test: Partial-output refinement

Second round of the inpainting comparison, following **Criteria2** in the
`Experiment_Pretrain` doc. Round 1 rated 27 outputs (9 prompts × 3 models) as
Pass, Partial or Fail. This round takes the **12 Partial outputs** and
regenerates the furniture with a corrected prompt, to see which model can fix
the remaining requirement without breaking what was already right.

## Inputs

| Folder / file | Contents |
|---|---|
| `regen_image/1024p/` | 7 Partial outputs from FLUX (`F1024p_*`) and SDXL (`S1024p_*`), lossless PNG copies from round 1 |
| `regen_image/512p/` | 5 Partial outputs from Kandinsky (`K512p_*`) |
| `manifest_regen_1024p.json` | 7 start images × 3 seeds = **21 entries**, run by both FLUX and SDXL |
| `manifest_regen_512p.json` | 5 start images × 3 seeds = **15 entries**, run by Kandinsky |

Masks are the round-1 masks in `mask/`, chosen by case and resolution:

| Cases | Furniture | 1024p mask | 512p mask |
|---|---|---|---|
| 1–4 | Bed | `mask/1024p/TestBed1k_002_mask.png` | `mask/512p/TestBed.5k_002_mask.png` |
| 5–7 | Sofa | `mask/1024p/TestSofa1k_005_mask.png` | `mask/512p/TestSofa.5k_005_mask.png` |
| 8–9 | Table | `mask/1024p/TestTable1k_003_mask.png` | `mask/512p/TestTable.5k_003_mask.png` |

## Manifest fields

The launchers read `id`, `level`, `seed`, `image`, `mask` and `prompt`.
The other fields are for review:

- `level` = start image + seed (e.g. `F1024p_5_L2_s42`), so output names never collide
- `start_image`, `source_model`, `case`, `furniture`
- `original_image`: the untouched room photo, for SSIM / LPIPS
- `fix_needed`, `must_stay`: from Table 3 in Criteria2

## Settings

- Seeds: 42, 123, 2024 (the same for every model)
- Prompts describe the **whole** piece of furniture (the fix plus everything in
  "must stay"), because the round-1 masks regenerate the whole object
- Tables are called "coffee table", not "dining table"
- FLUX: no negative prompt, guidance 30, 50 steps
- SDXL: `strength=1.0` (round 1 used 0.99), default negative prompt
- Kandinsky: default negative prompt, 512p

## Run (on Slurm, from `~/Sozo-Training`)

```bash
bash slurm/run_flux_regen_1024p.sh       # 21 jobs
bash slurm/run_sdxl_regen_1024p.sh       # 21 jobs
bash slurm/run_kandinsky_regen_512p.sh   # 15 jobs
```

Outputs:

```
outputs/images/regen/flux_1024p/{id}_{level}.png      e.g. 1_F1024p_5_L2_s42.png
outputs/images/regen/sdxl_1024p/{id}_{level}.png
outputs/images/regen/kandinsky_512p/{id}_{level}.png
outputs/logs/                                          same as round 1
```

## Script changes for this round

- `job_flux.sbatch`, `job_sdxl.sbatch`, `job_kandinsky.sbatch`: pass `--seed`
  when `SEED` is set. Without `SEED`, they behave as before.
- `job_sdxl.sbatch`: passes `--strength` (default 0.99, as in round 1).
  The regen launcher sets `STRENGTH=1.0`.
- `scripts/inpaint.py`: new `--strength` option, accepted only with `--model sdxl`.

## Known limitation

The round-1 masks also cover the fireplace, nightstand and lamp (bed) and the
coffee table (sofa), so those objects can change again. The nightstand and
coffee-table restore step from Criteria2 is skipped, because the mask would
regenerate those pixels anyway.
