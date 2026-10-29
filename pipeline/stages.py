"""The pipeline's stages and their contracts.

A stage reads files by name from the files the stages before it wrote, and
writes files by name for the stages after it. Every implementation of a stage,
whichever team writes it and in whichever language, reads at least what the
stage needs and writes at least what the stage makes, so that any
implementation of a stage runs with any implementation of the others.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Stage:
    name: str
    day: int
    needs: tuple[str, ...]
    makes: tuple[str, ...]
    summary: str


#: The stages, in the order the pipeline runs them.
STAGES = (
    Stage("sequence", 1, ("protocol.toml",), ("sequence.seq", "bvals", "bvecs"),
          "Design the diffusion acquisition as a Pulseq sequence."),
    Stage("simulation", 2, ("sequence.seq", "bvals", "bvecs", "phantom.phantom"), ("raw.h5",),
          "Simulate the sequence on the placenta phantom."),
    Stage("motion", 3, ("raw.h5", "sequence.seq", "bvals", "bvecs"), ("raw.h5",),
          "Correct the raw data for motion."),
    Stage("reconstruction", 2, ("raw.h5", "sequence.seq", "bvals", "bvecs"), ("dwi.nii.gz",),
          "Reconstruct the diffusion-weighted images."),
    Stage("analysis", 4, ("dwi.nii.gz", "bvals", "bvecs"), ("adc.nii.gz", "metrics.json"),
          "Fit the diffusion parameters and measure the images' quality."),
)

BY_NAME = {stage.name: stage for stage in STAGES}
