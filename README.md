# MRI TogetherThon 2026: the pipeline

The open-source, end-to-end pipeline for placenta diffusion MRI that the
[MRI TogetherThon](https://mritogether.esmrmb.org/26m/) builds, from the
sequence to the analysis. Teams build its stages during days 1 to 4, and on
day 5 the stages are joined into one pipeline.

Everything here runs in the TogetherThon's environment: set it up first, as
[mritogetherthon](https://github.com/mcencini/mritogetherthon) explains.

## The stages

The pipeline runs five stages, one after the other. Each reads files by name
from the stages before it and writes files by name for the stages after it: its
contract, in its folder's README. Any implementation that honours its stage's
contract runs with any implementation of the others.

| Stage | Day | Reads | Writes |
|---|---|---|---|
| [`sequence`](stages/sequence) | 1 | `protocol.toml` | `sequence.seq`, `bvals`, `bvecs` |
| [`simulation`](stages/simulation) | 2 | `sequence.seq`, `bvals`, `bvecs`, `phantom.phantom` | `raw.h5` |
| [`motion`](stages/motion) | 3 | `raw.h5`, `sequence.seq`, `bvals`, `bvecs` | `raw.h5` |
| [`reconstruction`](stages/reconstruction) | 2 | `raw.h5`, `sequence.seq`, `bvals`, `bvecs` | `dwi.nii.gz` |
| [`analysis`](stages/analysis) | 4 | `dwi.nii.gz`, `bvals`, `bvecs` | `adc.nii.gz`, `metrics.json` |

The contracts are a draft, to be settled with the speakers before the
TogetherThon.

## Working as a team

Each team works in its own folder, `stages/<stage>/<team>/`, so that the
teams' pull requests never conflict, whether a stage has one team or several.

1. The team lead forks this repository, adds the teammates to the fork, and
   starts the team's implementation:

   ```bash
   python -m pipeline new <stage> <team>                    # in Python
   python -m pipeline new <stage> <team> --language julia   # in Julia
   ```

2. The team writes its `run.py` (or `run.jl`), and runs it on the files the
   chosen implementations of the stages before it write:

   ```bash
   python -m pipeline check <stage>/<team>
   ```

   which also checks the files it writes against the stage's contract.
3. The team pushes to its fork, and opens a pull request by the end of each
   day. Its checks run the team's implementation in the same environment, and
   accept a pull request that changes the team's own folder alone.

Use the packages of the environment. A package that is missing is asked for in
the environment's
[Discussions](https://github.com/mcencini/mritogetherthon/discussions), and
added there for everyone.

## Day 5: joining the stages

`pipeline.toml` names the implementation the pipeline runs for each stage.

- **A stage with one team** is merged as it is.
- **A stage with several teams** is decided first: `python -m pipeline compare
  <stage>` runs each implementation with the chosen ones of the other stages
  and tabulates the analysis' `metrics.json` of each. The stage's teams then
  choose one, or merge the best parts of several.

```bash
python -m pipeline run                          # the implementations pipeline.toml names
python -m pipeline run --use motion=<team>      # ... with another team's motion correction
python -m pipeline list                         # the stages and their implementations
```

Each stage's results are kept in `outputs/`, and reused while neither its
implementation nor anything before it has changed.

## How a stage is run

The pipeline runs the command of the implementation's `stage.toml` in its
folder, with one argument: the path of an `inputs.toml` that holds

- `output`: the folder to write the stage's files to,
- `[inputs]`: the path of every file of the run so far, by name: the files of
  [`data/`](data), and those the stages before it wrote,
- `[parameters]`: `data/protocol.toml`.

Every file a stage writes reaches the stages after it, under its name.
