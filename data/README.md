# Data

The files every run of the pipeline starts from, by name, which the
organisers add before the TogetherThon:

- `protocol.toml`: the acquisition's parameters, which every stage receives as
  its `[parameters]`.
- `phantom.phantom`: the placenta phantom the simulation stage reads.

Keep large files out of git: publish them, for example on Zenodo, and add here
the small script that downloads them.
