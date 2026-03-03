#!/usr/bin/env python3
"""Download, build, and run a System Under Test (SUT)."""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys

from pathlib import Path
from typing import Any

import yaml


# --- Configuration ---
SUT_BASE_DIR = Path("SUT")


def print_help() -> None:
    """Print usage help text."""
    help_text = """
Usage: run_sut.py [--help|--explain] config_file

This script downloads, builds, and runs a System Under Test (SUT) based on a YAML configuration file.

Required arguments:
  config_file            Path to the SUT configuration YAML file

Optional arguments:
  --help, --explain      Show this help message and exit

The configuration YAML file must contain:
  - sut_name: Name of the SUT
  - github_repo: GitHub repository URL or local path
  - prerequisites_script: Script to run for prerequisites
  - run_script: Script to run the SUT

Optional YAML fields:
  - prerequisites_interpreter: Interpreter for prerequisites script
  - run_interpreter: Interpreter for run script
  - git_ref: Git reference to checkout
  - prerequisites_args: Arguments for prerequisites script
  - run_args: Arguments for run script
"""
    print(help_text)


def load_config(config_path: str) -> dict[str, Any]:
    """Load and validate the SUT configuration YAML file."""
    config_file = Path(config_path)
    if not config_file.exists():
        print(f"Error: Configuration file not found at {config_path}", file=sys.stderr)
        sys.exit(1)
    try:
        with config_file.open() as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML configuration file: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading configuration file: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(config, dict):
        print("Error: Configuration file must contain a YAML mapping.", file=sys.stderr)
        sys.exit(1)

    required_keys = ["sut_name", "github_repo", "prerequisites_script", "run_script"]
    for key in required_keys:
        if key not in config:
            print(f"Error: Missing required key '{key}' in configuration file.", file=sys.stderr)
            sys.exit(1)

    config.setdefault("prerequisites_interpreter", None)
    config.setdefault("run_interpreter", None)
    config.setdefault("git_ref", None)
    config.setdefault("prerequisites_args", "")
    config.setdefault("run_args", "")
    return config


def run_command(
    command: list[str] | str,
    cwd: str | None = None,
    check: bool = True,
    shell: bool = False,
    capture_output_flag: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a shell command."""
    cmd_str = " ".join(command) if not shell and isinstance(command, list) else command
    if not capture_output_flag:
        print(f"Executing (output will stream): {cmd_str} {'in ' + cwd if cwd else ''}")
    else:
        print(f"Executing: {cmd_str} {'in ' + cwd if cwd else ''}")

    try:
        process = subprocess.run(
            command if not shell else cmd_str, cwd=cwd, text=True,
            capture_output=capture_output_flag, shell=shell, check=False,
        )

        if capture_output_flag:
            if process.stdout and process.stdout.strip():
                print(process.stdout.strip())
            if process.stderr and process.stderr.strip():
                if process.returncode != 0:
                    print(process.stderr.strip(), file=sys.stderr)
                else:
                    print(process.stderr.strip())

        if check and process.returncode != 0:
            if not capture_output_flag or not (process.stderr and process.stderr.strip()):
                print(f"Error: Command '{cmd_str}' failed with exit code {process.returncode}", file=sys.stderr)
            sys.exit(1)
        return process
    except FileNotFoundError:
        err_cmd = command[0] if isinstance(command, list) and command else command
        print(f"Error: Command or script not found: {err_cmd}. Is it in your PATH or executable?", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\nCommand '{cmd_str}' interrupted by user (Ctrl+C).", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"An unexpected error occurred while running command '{cmd_str}': {e}", file=sys.stderr)
        sys.exit(1)


def _download_or_update_sut(config: dict[str, Any], sut_dir: Path) -> None:  # noqa: PLR0912
    """Download or update the SUT from git or local path."""
    github_repo_source = config["github_repo"]
    git_ref = config.get("git_ref")

    source_path = Path(github_repo_source)
    if source_path.is_dir():
        abs_source = source_path.resolve()
        print(f"Using local SUT path: {abs_source}")
        if sut_dir.exists():
            print(f"Removing existing SUT directory: {sut_dir} to ensure a fresh copy.")
            try:
                shutil.rmtree(sut_dir)
            except OSError as e:
                print(f"Error removing directory {sut_dir}: {e}", file=sys.stderr)
                sys.exit(1)

        print(f"Copying SUT from {abs_source} to {sut_dir}")
        try:
            shutil.copytree(abs_source, sut_dir)
        except OSError as e:
            print(f"Error copying local SUT from {abs_source} to {sut_dir}: {e}", file=sys.stderr)
            sys.exit(1)

        if git_ref:
            print(f"Note: 'git_ref' ('{git_ref}') is specified in config, but will be ignored for local SUT paths.")

    else:
        sut_dir_str = str(sut_dir)
        if not sut_dir.exists():
            print(f"SUT directory {sut_dir} not found. Cloning repository from {github_repo_source}...")
            clone_command = ["git", "clone", github_repo_source, sut_dir_str]
            run_command(clone_command, capture_output_flag=True)
            if git_ref:
                print(f"Checking out specified git reference: {git_ref}...")
                run_command(["git", "-C", sut_dir_str, "checkout", git_ref], capture_output_flag=True)
        else:
            print(f"SUT directory {sut_dir} exists. Updating repository from {github_repo_source}...")
            run_command(["git", "-C", sut_dir_str, "fetch", "--all", "--prune"], capture_output_flag=True)
            if git_ref:
                print(f"Checking out specified git reference: {git_ref}...")
                run_command(["git", "-C", sut_dir_str, "checkout", git_ref], capture_output_flag=True)

                is_branch_proc = run_command(
                    ["git", "-C", sut_dir_str, "show-ref", "--verify", "--quiet", f"refs/heads/{git_ref}"],
                    check=False, capture_output_flag=True,
                )
                is_remote_branch_proc = run_command(
                    ["git", "-C", sut_dir_str, "show-ref", "--verify", "--quiet", f"refs/remotes/origin/{git_ref}"],
                    check=False, capture_output_flag=True,
                )

                if is_branch_proc.returncode == 0 or is_remote_branch_proc.returncode == 0:
                    print(f"Reference {git_ref} appears to be a branch. Pulling updates...")
                    run_command(["git", "-C", sut_dir_str, "pull"], capture_output_flag=True)
                else:
                    print(f"Reference {git_ref} appears to be a tag or commit. Skipping pull.")
            else:
                print("No specific git_ref. Pulling updates for the current branch...")
                run_command(["git", "-C", sut_dir_str, "pull"], capture_output_flag=True)


def _make_executable(script_path: Path) -> None:
    """Make a script executable on POSIX systems if it isn't already."""
    if os.name == "posix" and not os.access(script_path, os.X_OK):
        print(f"Script {script_path} is not executable. Attempting to make it executable...")
        try:
            script_path.chmod(script_path.stat().st_mode | 0o111)
        except Exception as e:
            print(f"Warning: Failed to make script executable: {e}. Execution might fail.", file=sys.stderr)


def _run_script(
    config: dict[str, Any],
    script_key: str,
    interpreter_key: str,
    args_key: str,
    *,
    capture_output: bool = True,
) -> None:
    """Build and run a script command from config keys."""
    script_file = config[script_key]
    sut_abs_path = config["sut_abs_path"]
    script_path = Path(sut_abs_path) / script_file
    script_path = script_path.resolve()
    interpreter = config.get(interpreter_key)
    args_str = config.get(args_key, "")

    if not script_file.strip():
        if script_key == "run_script":
            print(f"Error: No SUT run script specified ({script_key} is empty). Cannot proceed.", file=sys.stderr)
            sys.exit(1)
        print(f"No script specified ({script_key} is empty). Skipping.")
        return

    if not script_path.is_file():
        print(
            f"Error: Script '{script_file}' not found or is not a file at '{script_path}'",
            file=sys.stderr,
        )
        sys.exit(1)

    command: list[str] = []
    if interpreter:
        command.append(interpreter)
    elif os.name == "posix":
        _make_executable(script_path)
    command.append(str(script_path))

    if args_str:
        try:
            command.extend(shlex.split(args_str))
        except Exception as e:
            print(f"Error splitting args '{args_str}': {e}", file=sys.stderr)
            sys.exit(1)

    print(f"Executing script: {script_file} with args: '{args_str}'")
    run_command(command, cwd=sut_abs_path, check=True, capture_output_flag=capture_output)


def main() -> None:
    """Download, build, and run a System Under Test."""
    parser = argparse.ArgumentParser(description="Download, build, and run a System Under Test (SUT).", add_help=False)
    parser.add_argument("config_file", nargs="?", help="Path to the SUT configuration YAML file.")
    parser.add_argument("--help", "--explain", action="store_true", help="Show help message and exit")
    args = parser.parse_args()

    if args.help or not args.config_file:
        print_help()
        sys.exit(0)

    config = load_config(args.config_file)
    sut_name = config["sut_name"]

    print(f"--- Processing SUT: {sut_name} ---")
    print(f"Configuration loaded from: {Path(args.config_file).resolve()}")

    # --- SUT Download/Update ---
    print("\n--- SUT Download/Update ---")

    SUT_BASE_DIR.mkdir(parents=True, exist_ok=True)

    sut_dir = SUT_BASE_DIR / sut_name
    config["sut_abs_path"] = str(sut_dir.resolve())

    _download_or_update_sut(config, sut_dir)

    print(f"SUT is ready at: {config['sut_abs_path']}")

    # --- Prerequisites/Build ---
    print("\n--- Prerequisites/Build ---")
    _run_script(config, "prerequisites_script", "prerequisites_interpreter", "prerequisites_args")
    print("Prerequisite script executed successfully.")

    # --- Run SUT ---
    print("\n--- Run SUT ---")
    print("SUT output will stream below. Press Ctrl+C to attempt to stop the SUT and this script.")
    _run_script(config, "run_script", "run_interpreter", "run_args", capture_output=False)

    print("SUT script execution finished.")
    print(f"\n--- SUT processing finished for: {sut_name} ---")


if __name__ == "__main__":
    main()
