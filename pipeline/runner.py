"""Runs implementations of the stages one after the other.

Each implementation lives in ``stages/<stage>/<team>/`` with a ``stage.toml``
naming the command that runs it. The runner gives the command one argument, the
path of an ``inputs.toml`` that holds:

- ``output``: the folder the implementation writes its files to,
- ``[inputs]``: the path of every file the stages before it wrote, by name,
- ``[parameters]``: the protocol, ``data/protocol.toml``, when there is one.

A run starts from the files in ``data/``, by name.

The runner then checks the files the stage must make, and hands every file the
implementation wrote to the stages after it, under the same name.

A stage's results are kept in ``outputs/`` and reused while neither its
implementation, nor anything before it in the run, has changed.
"""

import hashlib
import json
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path

from .stages import STAGES
from .validate import ContractError, check

ROOT = Path(__file__).resolve().parent.parent
#: The order in which a stage's files are checked, so that each check finds
#: the files it compares against.
CHECK_ORDER = ["bvals", "bvecs", "sequence.seq", "raw.h5", "dwi.nii.gz", "adc.nii.gz", "metrics.json"]


class StageFailed(Exception):
    pass


def implementations(stage):
    """The teams with an implementation of ``stage``."""
    folder = ROOT / "stages" / stage
    return sorted(p.name for p in folder.iterdir()
                  if (p / "stage.toml").is_file() and not p.name.startswith("_")) if folder.is_dir() else []


def choices(config=ROOT / "pipeline.toml"):
    """The implementation pipeline.toml chooses for each stage it names."""
    return dict(tomllib.loads(Path(config).read_text()).get("choose", {}))


def _digest(*parts):
    digest = hashlib.sha256()
    for part in parts:
        if isinstance(part, Path):
            files = sorted(p for p in part.rglob("*") if p.is_file() and "__pycache__" not in p.parts) \
                if part.is_dir() else [part]
            for file in files:
                digest.update(str(file.relative_to(ROOT)).encode())
                digest.update(file.read_bytes())
        else:
            digest.update(str(part).encode())
    return digest.hexdigest()[:16]


def _toml(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_toml(v) for v in value) + "]"
    return json.dumps(str(value))


def _write_toml(path, data):
    lines = []

    def table(prefix, values):
        scalars = {k: v for k, v in values.items() if not isinstance(v, dict)}
        tables = {k: v for k, v in values.items() if isinstance(v, dict)}
        if prefix:
            lines.append(f"\n[{prefix}]")
        lines.extend(f"{json.dumps(k)} = {_toml(v)}" for k, v in scalars.items())
        for key, sub in tables.items():
            table(f"{prefix}.{json.dumps(key)}" if prefix else json.dumps(key), sub)

    table("", data)
    Path(path).write_text("\n".join(lines) + "\n")


class Runner:
    def __init__(self, outputs=ROOT / "outputs", log=print):
        self.outputs = Path(outputs)
        self.log = log
        protocol = ROOT / "data" / "protocol.toml"
        self.protocol = tomllib.loads(protocol.read_text()) if protocol.is_file() else {}

    def chain(self, chosen, until=None):
        """Run the stages with the implementations ``chosen``, up to ``until``.

        Return the files of the run by name, and the folder of each stage."""
        files = {p.name: p for p in sorted((ROOT / "data").glob("*"))
                 if p.is_file() and p.name != "README.md"}
        key = _digest(*files.values())
        folders = {}
        for stage in STAGES:
            team = chosen.get(stage.name)
            if team is None:
                raise StageFailed(f"{stage.name}: pipeline.toml chooses no implementation of it yet; "
                                  f"choose one there, or run with --use {stage.name}=<team>")
            folder = ROOT / "stages" / stage.name / team
            if not (folder / "stage.toml").is_file():
                raise StageFailed(f"{stage.name}: there is no implementation stages/{stage.name}/{team}/stage.toml")
            key = _digest(key, stage.name, team, folder)
            out = self.outputs / f"{stage.name}-{team}-{key}"
            folders[stage.name] = out
            files.update(self._stage(stage, team, folder, files, out))
            if stage.name == until:
                break
        return files, folders

    def _stage(self, stage, team, folder, files, out):
        manifest = out / "manifest.json"
        if manifest.is_file():
            self.log(f"· {stage.name} ({team}): unchanged, reusing {out.relative_to(ROOT)}")
            return {name: out / name for name in json.loads(manifest.read_text())}

        missing = [name for name in stage.needs if name not in files]
        if missing:
            raise StageFailed(f"{stage.name}: neither data/ nor the stages before it hold {', '.join(missing)}")
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)
        inputs = out / "inputs.toml"
        _write_toml(inputs, {"output": str(out),
                             "inputs": {name: str(path) for name, path in files.items()},
                             "parameters": self.protocol})
        command = tomllib.loads((folder / "stage.toml").read_text())["command"]

        self.log(f"▶ {stage.name} ({team}): {' '.join(command)}")
        started = time.monotonic()
        with open(out / "log.txt", "w") as log:
            process = subprocess.Popen([*command, str(inputs)], cwd=folder, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True, bufsize=1)
            for line in process.stdout:
                log.write(line)
                self.log("  │ " + line.rstrip())
            code = process.wait()
        if code != 0:
            raise StageFailed(f"{stage.name} ({team}) exited with {code}: see {(out / 'log.txt').relative_to(ROOT)}")

        written = {p.name: p for p in out.iterdir()
                   if p.is_file() and p.name not in ("inputs.toml", "log.txt", "manifest.json")}
        absent = [name for name in stage.makes if name not in written]
        if absent:
            raise StageFailed(f"{stage.name} ({team}) did not write {', '.join(absent)}")
        merged = {**files, **written}
        for name in sorted(written, key=lambda n: CHECK_ORDER.index(n) if n in CHECK_ORDER else len(CHECK_ORDER)):
            try:
                check(name, written[name], merged)
            except ContractError as error:
                raise StageFailed(f"{stage.name} ({team}) wrote {name} against the contract: {error}") from None
        manifest.write_text(json.dumps(sorted(written)))
        self.log(f"✔ {stage.name} ({team}) in {time.monotonic() - started:.0f} s: {', '.join(sorted(written))}")
        return written


def fail(message):
    print(f"✘ {message}", file=sys.stderr)
    raise SystemExit(1)

