# Analysis (day 4)

Fit the diffusion parameters and measure the images' quality.

| | |
|---|---|
| **Reads** | `dwi.nii.gz`, `bvals`, `bvecs` |
| **Writes** | `adc.nii.gz`, `metrics.json`, and any further maps |

- `adc.nii.gz`: NIfTI, the voxels of `dwi.nii.gz`, in mm²/s, NaN where there
  is no fit.
- `metrics.json`: one JSON object of named numbers (or strings). The
  pipeline's `compare` command tabulates them for each implementation of a
  stage, so they are what decides between implementations: name them, and
  their units, the same way across teams.
