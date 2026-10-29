# {team}'s {stage}: {summary}
#
# The pipeline runs this as `julia run.jl inputs.toml`. It reads {needs}
# and writes {makes} to the output folder; see stages/{stage}/README.md.
using TOML

config = TOML.parsefile(ARGS[1])
inputs = config["inputs"]          # every file so far, by name
parameters = config["parameters"]  # data/protocol.toml
output = config["output"]          # write your files here

error("{stage}: write {makes} to the output folder")
