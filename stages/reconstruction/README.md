# Reconstruction (day 2)

Reconstruct the diffusion-weighted images.

| | |
|---|---|
| **Reads** | `raw.h5`, `sequence.seq`, `bvals`, `bvecs` |
| **Writes** | `dwi.nii.gz` |

- `dwi.nii.gz`: NIfTI, x × y × z × volumes, the volumes in the order of
  `bvals`, with finite values.
