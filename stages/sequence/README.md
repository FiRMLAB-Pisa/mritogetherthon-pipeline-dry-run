# Sequence (day 1)

Design the diffusion acquisition as a Pulseq sequence.

| | |
|---|---|
| **Reads** | `protocol.toml` (also given as the `[parameters]` of `inputs.toml`) |
| **Writes** | `sequence.seq`, `bvals`, `bvecs` |

- `sequence.seq`: a Pulseq file. Its ADC events split into as many equal
  volumes as there are b-values, acquired one volume after the other.
- `bvals`: FSL's format, one line with the b-value of each volume, in s/mm².
- `bvecs`: FSL's format, three lines with the unit direction of each volume
  (zero for b = 0).
