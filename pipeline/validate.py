"""Checks that a stage's files are what the stages after it expect.

Each check takes the file and the files the run holds so far, and raises
ContractError naming what is wrong. They check the form of the files, not the
quality of their content: that is the analysis stage's work.
"""

import json
from pathlib import Path

import numpy as np


class ContractError(Exception):
    pass


def _bvals(files):
    return np.atleast_1d(np.loadtxt(files["bvals"]))


def check_bvals(path, files):
    bvals = np.atleast_1d(np.loadtxt(path))
    if bvals.ndim != 1 or len(bvals) == 0:
        raise ContractError("bvals must hold one line of b-values, one per volume")
    if np.any(bvals < 0):
        raise ContractError("b-values must not be negative")


def check_bvecs(path, files):
    bvecs = np.loadtxt(path, ndmin=2)
    count = len(_bvals(files))
    if bvecs.shape != (3, count):
        raise ContractError(f"bvecs must hold 3 lines of {count} values, one per volume: it holds {bvecs.shape}")
    norms = np.linalg.norm(bvecs, axis=0)
    if not np.all(np.isclose(norms, 1, atol=1e-3) | np.isclose(norms, 0)):
        raise ContractError("each direction in bvecs must be a unit vector, or zero for b = 0")


def check_sequence(path, files):
    import pypulseq as pp

    seq = pp.Sequence()
    seq.read(str(path))
    adcs = sum(1 for index in seq.block_events if seq.get_block(index).adc is not None)
    volumes = len(_bvals(files))
    if adcs == 0:
        raise ContractError("the sequence holds no ADC event")
    if adcs % volumes:
        raise ContractError(f"the sequence's {adcs} ADC events do not split into {volumes} volumes, one per b-value")


def _acquisitions(path):
    import ismrmrd

    dataset = ismrmrd.Dataset(str(path), "dataset", create_if_needed=False)
    try:
        return [dataset.read_acquisition(i) for i in range(dataset.number_of_acquisitions())]
    finally:
        dataset.close()


def check_raw(path, files):
    acquisitions = _acquisitions(path)
    if not acquisitions:
        raise ContractError("raw.h5 holds no acquisition")
    volumes = len(_bvals(files))
    counters = [(int(a.idx.repetition), int(a.idx.kspace_encode_step_1)) for a in acquisitions]
    repetitions = {r for r, _ in counters}
    if repetitions != set(range(volumes)):
        raise ContractError(f"idx.repetition must number the {volumes} volumes 0 to {volumes - 1}: it holds {sorted(repetitions)}")
    lines = {line for _, line in counters}
    if len(set(counters)) != len(counters) or len(counters) != volumes * len(lines):
        raise ContractError("each volume must hold each k-space line once, numbered by idx.kspace_encode_step_1")


def check_dwi(path, files):
    import nibabel as nib

    image = nib.load(str(path))
    shape = image.shape if len(image.shape) == 4 else (*image.shape, 1)
    volumes = len(_bvals(files))
    if len(shape) != 4 or shape[3] != volumes:
        raise ContractError(f"dwi.nii.gz must be x × y × z × {volumes} volumes: it is {image.shape}")
    if not np.all(np.isfinite(image.get_fdata())):
        raise ContractError("dwi.nii.gz holds values that are not finite")


def check_adc(path, files):
    import nibabel as nib

    adc = nib.load(str(path))
    dwi = nib.load(str(files["dwi.nii.gz"]))
    if adc.shape[:3] != dwi.shape[:3]:
        raise ContractError(f"adc.nii.gz must have the images' {dwi.shape[:3]} voxels: it has {adc.shape[:3]}")
    if np.any(np.isinf(adc.get_fdata())):
        raise ContractError("adc.nii.gz holds infinite values; use NaN where there is no fit")


def check_metrics(path, files):
    try:
        metrics = json.loads(Path(path).read_text())
    except json.JSONDecodeError as error:
        raise ContractError(f"metrics.json is not JSON: {error}") from None
    if not isinstance(metrics, dict) or not all(isinstance(v, (int, float, str)) for v in metrics.values()):
        raise ContractError("metrics.json must be one object of named numbers or strings")


CHECKS = {
    "bvals": check_bvals,
    "bvecs": check_bvecs,
    "sequence.seq": check_sequence,
    "raw.h5": check_raw,
    "dwi.nii.gz": check_dwi,
    "adc.nii.gz": check_adc,
    "metrics.json": check_metrics,
}


def check(name, path, files):
    """Check the file ``name`` a stage wrote at ``path``, against ``files``."""
    if name in CHECKS:
        CHECKS[name](path, files)
