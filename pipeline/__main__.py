"""The pipeline's command line.

    python -m pipeline run                      run the implementations pipeline.toml chooses
    python -m pipeline run --use motion=team-a  ... with team-a's motion correction instead
    python -m pipeline check motion/team-a      run team-a's stage on the chosen stages' results
    python -m pipeline compare analysis         run every implementation of a stage and compare
    python -m pipeline new motion team-a        start team-a's implementation of a stage
    python -m pipeline list                     list the stages and their implementations
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

from .runner import ROOT, Runner, StageFailed, choices, fail, implementations
from .stages import BY_NAME, STAGES

TEAM = re.compile(r"^[a-z0-9][a-z0-9-]{1,38}$")


def _uses(values):
    chosen = choices()
    for value in values or []:
        stage, _, team = value.partition("=")
        if stage not in BY_NAME or not team:
            fail(f"--use takes stage=team, with a stage among {', '.join(BY_NAME)}: not {value}")
        chosen[stage] = team
    return chosen


def _split(target):
    stage, _, team = target.strip("/").removeprefix("stages/").partition("/")
    if stage not in BY_NAME or not team:
        fail(f"name an implementation as stage/team, with a stage among {', '.join(BY_NAME)}: not {target}")
    return stage, team


def command_run(args):
    chosen = _uses(args.use)
    try:
        files, folders = Runner().chain(chosen)
    except StageFailed as error:
        fail(str(error))
    print("\nThe pipeline ran:")
    for stage in STAGES:
        print(f"  {stage.name:15} {chosen[stage.name]:20} {folders[stage.name].relative_to(ROOT)}")
    metrics = json.loads(files["metrics.json"].read_text())
    print("\n" + "\n".join(f"  {name}: {value}" for name, value in metrics.items()))


def command_check(args):
    chosen = _uses(args.use)
    runner = Runner()
    failed = []
    for target in args.implementations:
        stage, team = _split(target)
        print(f"\n━━ {stage}/{team}")
        try:
            _, folders = runner.chain({**chosen, stage: team}, until=stage)
            print(f"✔ {stage}/{team} honours the contract: {folders[stage].relative_to(ROOT)}")
        except StageFailed as error:
            print(f"✘ {error}")
            failed.append(f"{stage}/{team}")
    if failed:
        fail(f"{len(failed)} implementation(s) failed: {', '.join(failed)}")


def command_compare(args):
    """Run each implementation of the stages named, with the chosen ones of the
    other stages, and tabulate the analysis' metrics of each run."""
    chosen = choices()
    runner = Runner()
    stages = args.stages or [s.name for s in STAGES if len(implementations(s.name)) > 1]
    report = []
    for stage in stages:
        teams = implementations(stage)
        rows = {}
        for team in teams:
            try:
                files, _ = runner.chain({**chosen, stage: team})
                rows[team] = json.loads(files["metrics.json"].read_text())
            except StageFailed as error:
                rows[team] = {"failed": str(error)}
        names = sorted({name for metrics in rows.values() for name in metrics})
        report.append(f"### {stage}\n")
        report.append("| implementation | " + " | ".join(names) + " |")
        report.append("|---" * (len(names) + 1) + "|")
        for team, metrics in rows.items():
            mark = " (chosen)" if chosen.get(stage) == team else ""
            cells = [_cell(metrics.get(name, "")) for name in names]
            report.append(f"| {team}{mark} | " + " | ".join(cells) + " |")
        report.append("")
    text = "\n".join(report) if report else "No stage has more than one implementation yet.\n"
    print(text)
    if args.summary:
        with open(args.summary, "a") as summary:
            summary.write("## Implementations compared\n\n" + text + "\n")


def _cell(value):
    return f"{value:.4g}" if isinstance(value, float) else str(value).replace("|", "\\|")


def command_new(args):
    stage = BY_NAME.get(args.stage) or fail(f"the stages are {', '.join(BY_NAME)}: not {args.stage}")
    if not TEAM.match(args.team) or args.team == "baseline":
        fail("a team's name is 2 to 39 lowercase letters, digits and dashes, and not 'baseline'")
    folder = ROOT / "stages" / stage.name / args.team
    if folder.exists():
        fail(f"{folder.relative_to(ROOT)} already exists")
    shutil.copytree(ROOT / "templates" / args.language, folder)
    for file in folder.rglob("*"):
        if file.is_file():
            text = file.read_text()
            for key, value in {"{stage}": stage.name, "{team}": args.team, "{summary}": stage.summary,
                               "{needs}": ", ".join(f"`{n}`" for n in stage.needs),
                               "{makes}": ", ".join(f"`{n}`" for n in stage.makes)}.items():
                text = text.replace(key, value)
            file.write_text(text)
    print(f"Created {folder.relative_to(ROOT)}. Run it with:\n  python -m pipeline check {stage.name}/{args.team}")


def command_list(args):
    chosen = choices()
    for stage in STAGES:
        teams = implementations(stage.name)
        marked = [f"{team} (chosen)" if team == chosen.get(stage.name) else team for team in teams]
        print(f"{stage.name:15} day {stage.day}  {', '.join(marked) or '-'}")


def command_scope(args):
    """Name the implementations a change touches, for the checks to run.

    A pull request from a fork must change one team's folder alone. A change
    to anything else, which the organisers make, checks every implementation."""
    changed = subprocess.run(["git", "diff", "--name-only", f"{args.base}...HEAD"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout.split()
    touched, other = set(), []
    for path in changed:
        parts = path.split("/")
        if len(parts) >= 4 and parts[0] == "stages" and parts[1] in BY_NAME and not parts[2].startswith("_"):
            touched.add((parts[1], parts[2]))
        else:
            other.append(path)
    if args.fork:
        problems = []
        if other:
            problems.append("it changes files outside a team's folder: " + ", ".join(other))
        if len(touched) > 1:
            problems.append("it changes several teams' folders: " + ", ".join(f"{s}/{t}" for s, t in sorted(touched)))
        if any(team == "baseline" for _, team in touched):
            problems.append("it changes a baseline, which the organisers keep")
        if problems:
            fail("A team's pull request changes its own folder, stages/<stage>/<team>/, alone; "
                 + "; ".join(problems) + ". Ask the organisers in Discussions for anything else.")
    if other and not args.fork:
        touched = {(s.name, team) for s in STAGES for team in implementations(s.name)}
    existing = sorted((s, t) for s, t in touched if (ROOT / "stages" / s / t / "stage.toml").is_file())
    print("\n".join(f"{s}/{t}" for s, t in existing))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m pipeline", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="run the whole pipeline")
    run.add_argument("--use", action="append", metavar="STAGE=TEAM", help="run TEAM's implementation of STAGE")
    run.set_defaults(handler=command_run)

    check = commands.add_parser("check", help="run implementations of a stage and check their files")
    check.add_argument("implementations", nargs="+", metavar="STAGE/TEAM")
    check.add_argument("--use", action="append", metavar="STAGE=TEAM",
                       help="run TEAM's implementation of an earlier STAGE")
    check.set_defaults(handler=command_check)

    compare = commands.add_parser("compare", help="compare the implementations of stages")
    compare.add_argument("stages", nargs="*", metavar="STAGE", help="default: every stage with several")
    compare.add_argument("--summary", default=os.environ.get("GITHUB_STEP_SUMMARY"), help=argparse.SUPPRESS)
    compare.set_defaults(handler=command_compare)

    new = commands.add_parser("new", help="start a team's implementation of a stage")
    new.add_argument("stage")
    new.add_argument("team")
    new.add_argument("--language", choices=["python", "julia"], default="python")
    new.set_defaults(handler=command_new)

    listing = commands.add_parser("list", help="list the stages and their implementations")
    listing.set_defaults(handler=command_list)

    scope = commands.add_parser("scope", help=argparse.SUPPRESS)
    scope.add_argument("--base", required=True)
    scope.add_argument("--fork", action="store_true")
    scope.set_defaults(handler=command_scope)

    args = parser.parse_args(argv)
    args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
