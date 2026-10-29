# Motion correction (day 3)

Correct the raw data for motion.

| | |
|---|---|
| **Reads** | `raw.h5`, `sequence.seq`, `bvals`, `bvecs` |
| **Writes** | `raw.h5`, corrected, as the simulation stage's contract describes it |

A correction that also rotates the diffusion directions writes `bvecs` too:
the stages after it then read the rotated ones.
