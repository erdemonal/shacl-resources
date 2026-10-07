import argparse
import csv
import importlib.metadata
import os
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from shacl_study import __version__
from shacl_study.discovery import config_digest, format_plan, load_config, plan_queries, run_discovery, select_queries
from shacl_study.github_client import API_VERSION, GitHubAuthError, GitHubClient
from shacl_study.logging_utils import configure_logging
from shacl_study.storage import write_manifest
from shacl_study.verification import (
    GitHubContent,
    config_sha256,
    load_verification_config,
    run_verification,
    select_code_signal,
    select_pilot,
)

NOT_IN_MILESTONE = ("inspect", "stats", "audit", "run-all")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="shacl_study")
    subparsers = parser.add_subparsers(dest="command", required=True)

    discover = subparsers.add_parser("discover", help="Discover candidate GitHub repositories.")
    discover.add_argument("--config", default="config/discovery_queries.yaml")
    discover.add_argument("--data-dir", default="data")
    discover.add_argument("--dry-run", action="store_true")
    discover.add_argument("--fresh", action="store_true", help="Ignore saved discovery state.")
    discover.add_argument("--max-pages", type=int, default=None)
    discover.add_argument("--per-page", type=int, default=100)
    discover.add_argument(
        "--query-id",
        action="append",
        default=None,
        help="Run one planned query id. Repeat to run several. Date partitions of a selected repository query still run.",
    )
    verify = subparsers.add_parser("verify", help="Inspect candidate repository content for SHACL.")
    verify.add_argument("--config", default="config/verification.yaml")
    verify.add_argument("--candidates", default="data/results/candidate_repositories.csv")
    verify.add_argument("--data-dir", default="data")
    verify.add_argument("--pilot", type=int, default=None, help="Inspect a stratified pilot of this many repositories.")
    verify.add_argument("--phase", type=int, choices=[1], default=None, help="Phase 1 verifies code-search repositories only.")
    verify.add_argument("--full-corpus", action="store_true")
    verify.add_argument("--fresh", action="store_true", help="Ignore saved verification state.")
    verify.add_argument("--repository-id", action="append", default=None)
    for name in NOT_IN_MILESTONE:
        subparsers.add_parser(name, help="Not implemented.")

    args = parser.parse_args(argv)
    if args.command in NOT_IN_MILESTONE:
        raise SystemExit(f"{args.command} is not implemented.")
    if args.command == "verify":
        _verify(args)
        return
    if args.max_pages is not None and args.max_pages < 1:
        raise SystemExit("--max-pages must be at least 1.")
    if args.per_page < 1 or args.per_page > 100:
        raise SystemExit("--per-page must be between 1 and 100.")

    config_path = Path(args.config)
    config = load_config(config_path)
    planned = select_queries(plan_queries(config), args.query_id)
    if args.query_id and not planned:
        raise SystemExit("No planned query matches --query-id.")

    if args.dry_run:
        sys.stdout.write(format_plan(planned))
        return

    _load_dotenv(Path(".env"))
    token = os.environ.get("GITHUB_TOKEN", "")
    data_dir = Path(args.data_dir)
    logger = configure_logging(data_dir / "logs" / "discovery.log")
    try:
        client = GitHubClient(token, data_dir / "raw" / "github-cache")
        state = run_discovery(
            config=config,
            config_sha256=config_digest(config_path),
            client=client,
            data_dir=data_dir,
            fresh=args.fresh,
            per_page=args.per_page,
            max_pages=args.max_pages,
            query_ids=args.query_id,
            window_end=date.today(),
            logger=logger,
        )
    except GitHubAuthError as exc:
        raise SystemExit(str(exc)) from exc

    manifest = _manifest(config_path, state.partition_window_start, state.partition_window_end)
    write_manifest(data_dir / "results" / "run_manifest.json", manifest)
    truncated = sum(1 for item in state.executions.values() if item.potentially_truncated)
    print(
        f"candidates={len(state.candidates)} "
        f"nonpublic={len(state.nonpublic)} "
        f"queries={len(state.executions)} "
        f"truncated_or_split={truncated}"
    )


def _verify(args) -> None:
    selected = [args.pilot is not None, args.phase is not None, args.full_corpus, bool(args.repository_id)]
    if sum(bool(item) for item in selected) != 1:
        raise SystemExit("Refusing an unscoped verification run. Pass --pilot N, --phase 1, or --repository-id. --full-corpus is separate.")
    if args.pilot is not None and args.full_corpus:
        raise SystemExit("Pass either --pilot or --full-corpus.")
    if args.pilot is not None and args.pilot < 1:
        raise SystemExit("--pilot must be at least 1.")
    config_path = Path(args.config)
    config = load_verification_config(config_path)
    with Path(args.candidates).open(encoding="utf-8", newline="") as handle:
        candidates = list(csv.DictReader(handle))
    if args.repository_id:
        wanted = set(args.repository_id)
        rows = [row for row in candidates if row["repository_id"] in wanted]
        missing = wanted - {row["repository_id"] for row in rows}
        if missing:
            raise SystemExit(f"Unknown repository id: {', '.join(sorted(missing))}")
    elif args.pilot is not None:
        rows = select_pilot(candidates, args.pilot)
    elif args.phase == 1:
        rows = select_code_signal(candidates)
        print(f"phase=1 code_signal_repositories={len(rows)}")
    else:
        rows = candidates
    if not rows:
        raise SystemExit("No repositories selected.")
    _load_dotenv(Path(".env"))
    token = os.environ.get("GITHUB_TOKEN", "")
    data_dir = Path(args.data_dir)
    logger = configure_logging(data_dir / "logs" / "verification.log")
    commit, dirty = _git_info(Path.cwd())
    try:
        client = GitHubClient(token, data_dir / "raw" / "github-cache")
        summary = run_verification(
            rows=rows,
            source=GitHubContent(client, config),
            vocab=None,
            config=config,
            config_digest=config_sha256(config_path),
            data_dir=data_dir,
            fresh=args.fresh,
            clock=lambda: datetime.now(timezone.utc),
            logger=logger,
            phase=str(args.phase or ""),
            git_commit=commit,
            git_dirty=dirty,
        )
    except GitHubAuthError as exc:
        raise SystemExit(str(exc)) from exc
    counts = " ".join(f"{key}={value}" for key, value in sorted(summary["status_counts"].items()))
    print(f"verified_repositories={summary['repository_count']} {counts}")


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def _manifest(config_path: Path, window_start: str, window_end: str) -> dict:
    commit, dirty = _git_info(Path.cwd())
    versions = {}
    for package in ("requests", "pydantic", "PyYAML"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return {
        "milestone": 1,
        "collected_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "software_version": __version__,
        "git_commit": commit,
        "git_dirty": dirty,
        "github_api_version": API_VERSION,
        "discovery_config_path": str(config_path),
        "discovery_config_sha256": config_digest(config_path),
        "partition_window_start": window_start,
        "partition_window_end": window_end,
        "python_version": sys.version,
        "dependency_versions": versions,
        "scope": "Discovery only. No SHACL verification or statistics.",
    }


def _git_info(cwd: Path) -> tuple[str | None, bool | None]:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=cwd, text=True, stderr=subprocess.DEVNULL
        ).strip()
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=cwd, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None, None
    return commit, bool(dirty)
