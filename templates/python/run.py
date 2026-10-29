"""{team}'s {stage}: {summary}

The pipeline runs this as `python run.py inputs.toml`. It reads {needs}
and writes {makes} to the output folder; see stages/{stage}/README.md.
"""

import sys
import tomllib
from pathlib import Path

config = tomllib.loads(Path(sys.argv[1]).read_text())
inputs = {name: Path(path) for name, path in config["inputs"].items()}  # every file so far, by name
parameters = config["parameters"]                                        # data/protocol.toml
output = Path(config["output"])                                          # write your files here

raise NotImplementedError("{stage}: write {makes} to the output folder")
