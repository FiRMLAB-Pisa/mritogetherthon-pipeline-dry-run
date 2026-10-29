# Simulation (day 2)

Simulate the sequence on the placenta phantom.

| | |
|---|---|
| **Reads** | `sequence.seq`, `bvals`, `bvecs`, `phantom.phantom` |
| **Writes** | `raw.h5` |

- `raw.h5`: ISMRMRD raw data, in the group `dataset`. Each acquisition is one
  k-space line, numbered by its counters: `idx.repetition` is its volume, from
  0, and `idx.kspace_encode_step_1` its line, from 0. Each volume holds each
  line once.

KomaMRI does not simulate diffusion by itself (the phantom's `Dλ1`, `Dλ2` and
`Dθ` are not used by its simulation, nor kept by `write_phantom`).
