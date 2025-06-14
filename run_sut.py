import argparse
import yaml
import os
import subprocess
import sys
import shlex
import shutil # Added for shutil.copytree and rmtree

# --- Configuration ---
SUT_BASE_DIR = "SUT"

def load_config(config_path):
    """Loads and validates the SUT configuration YAML file."""
    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found at {config_path}", file=sys.stderr)
        sys.exit(1)
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML configuration file: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading configuration file: {e}", file=sys.stderr)
        sys.exit(1)

    required_keys = ['sut_name', 'github_repo', 'prerequisites_script', 'run_script']
    for key in required_keys:
        if key not in config:
            print(f"Error: Missing required key '{key}' in configuration file.", file=sys.stderr)
            sys.exit(1)

    config.setdefault('prerequisites_interpreter', None)
    config.setdefault('run_interpreter', None)
    config.setdefault('git_ref', None)
    config.setdefault('prerequisites_args', '')
    config.setdefault('run_args', '')
    return config

def run_command(command, cwd=None, check=True, shell=False, capture_output_flag=True):
    """Helper function to run a shell command."""
    cmd_str = ' '.join(command) if not shell and isinstance(command, list) else command
    if not capture_output_flag:
        print(f"Executing (output will stream): {cmd_str} {'in ' + cwd if cwd else ''}")
    else:
        print(f"Executing: {cmd_str} {'in ' + cwd if cwd else ''}")

    try:
        process = subprocess.run(command if not shell else cmd_str,
                                 cwd=cwd,
                                 text=True,
                                 capture_output=capture_output_flag,
                                 shell=shell,
                                 check=False)

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

def main():
    parser = argparse.ArgumentParser(description="Download, build, and run a System Under Test (SUT).")
    parser.add_argument("config_file", help="Path to the SUT configuration YAML file.")
    args = parser.parse_args()

    config = load_config(args.config_file)
    sut_name = config['sut_name']
    github_repo_source = config['github_repo'] # Can be URL or local path
    git_ref = config.get('git_ref')

    print(f"--- Processing SUT: {sut_name} ---")
    print(f"Configuration loaded from: {os.path.abspath(args.config_file)}")

    # --- SUT Download/Update ---
    print("\n--- SUT Download/Update ---")

    if not os.path.exists(SUT_BASE_DIR):
        print(f"Creating SUT base directory: {SUT_BASE_DIR}")
        os.makedirs(SUT_BASE_DIR)

    sut_dir = os.path.join(SUT_BASE_DIR, sut_name)
    config['sut_abs_path'] = os.path.abspath(sut_dir)

    # Check if github_repo_source is a local directory
    if os.path.isdir(github_repo_source):
        abs_github_repo_source = os.path.abspath(github_repo_source)
        print(f"Using local SUT path: {abs_github_repo_source}")
        if os.path.exists(sut_dir):
            print(f"Removing existing SUT directory: {sut_dir} to ensure a fresh copy.")
            try:
                shutil.rmtree(sut_dir)
            except OSError as e:
                print(f"Error removing directory {sut_dir}: {e}", file=sys.stderr)
                sys.exit(1)

        print(f"Copying SUT from {abs_github_repo_source} to {sut_dir}")
        try:
            # copytree needs the destination directory to not exist yet.
            shutil.copytree(abs_github_repo_source, sut_dir)
        except OSError as e:
            print(f"Error copying local SUT from {abs_github_repo_source} to {sut_dir}: {e}", file=sys.stderr)
            sys.exit(1)

        if git_ref:
            print(f"Note: 'git_ref' ('{git_ref}') is specified in config, but will be ignored for local SUT paths.")

    else: # Not a local directory, assume it's a git repository URL
        if not os.path.exists(sut_dir):
            print(f"SUT directory {sut_dir} not found. Cloning repository from {github_repo_source}...")
            clone_command = ['git', 'clone', github_repo_source, sut_dir]
            run_command(clone_command, capture_output_flag=True)
            if git_ref:
                print(f"Checking out specified git reference: {git_ref}...")
                run_command(['git', '-C', sut_dir, 'checkout', git_ref], capture_output_flag=True)
        else:
            print(f"SUT directory {sut_dir} exists. Updating repository from {github_repo_source}...")
            run_command(['git', '-C', sut_dir, 'fetch', '--all', '--prune'], capture_output_flag=True)
            if git_ref:
                print(f"Checking out specified git reference: {git_ref}...")
                run_command(['git', '-C', sut_dir, 'checkout', git_ref], capture_output_flag=True)

                is_branch_proc = run_command(['git', '-C', sut_dir, 'show-ref', '--verify', '--quiet', f'refs/heads/{git_ref}'],
                                             check=False, capture_output_flag=True)
                is_remote_branch_proc = run_command(['git', '-C', sut_dir, 'show-ref', '--verify', '--quiet', f'refs/remotes/origin/{git_ref}'],
                                                    check=False, capture_output_flag=True)

                if is_branch_proc.returncode == 0 or is_remote_branch_proc.returncode == 0:
                     print(f"Reference {git_ref} appears to be a branch. Pulling updates...")
                     run_command(['git', '-C', sut_dir, 'pull'], capture_output_flag=True)
                else:
                    print(f"Reference {git_ref} appears to be a tag or commit. Skipping pull.")
            else:
                print("No specific git_ref. Pulling updates for the current branch...")
                run_command(['git', '-C', sut_dir, 'pull'], capture_output_flag=True)

    print(f"SUT is ready at: {config['sut_abs_path']}")

    # --- Prerequisites/Build ---
    print("\n--- Prerequisites/Build ---")
    prereq_script_file = config['prerequisites_script']
    prereq_script_path_abs = os.path.normpath(os.path.join(config['sut_abs_path'], prereq_script_file))
    prereq_interpreter = config.get('prerequisites_interpreter')
    prereq_args_str = config.get('prerequisites_args', '')

    if not prereq_script_file.strip():
        print("No prerequisite script specified (prerequisites_script is empty). Skipping.")
    elif not os.path.isfile(prereq_script_path_abs):
        print(f"Error: Prerequisite script '{prereq_script_file}' not found or is not a file at '{prereq_script_path_abs}'", file=sys.stderr)
        sys.exit(1)
    else:
        prereq_command = []
        if prereq_interpreter:
            prereq_command.append(prereq_interpreter)

        if not prereq_interpreter and os.name == 'posix':
            if not os.access(prereq_script_path_abs, os.X_OK):
                print(f"Prerequisite script {prereq_script_path_abs} is not executable. Attempting to make it executable...")
                try:
                    os.chmod(prereq_script_path_abs, os.stat(prereq_script_path_abs).st_mode | 0o111)
                except Exception as e:
                    print(f"Warning: Failed to make prerequisite script executable: {e}. Execution might fail.", file=sys.stderr)
        prereq_command.append(prereq_script_path_abs)

        if prereq_args_str:
            try:
                prereq_command.extend(shlex.split(prereq_args_str))
            except Exception as e:
                 print(f"Error splitting prerequisite_args '{prereq_args_str}': {e}", file=sys.stderr)
                 sys.exit(1)

        print(f"Executing prerequisite script: {prereq_script_file} with args: '{prereq_args_str}'")
        run_command(prereq_command, cwd=config['sut_abs_path'], capture_output_flag=True)
        print("Prerequisite script executed successfully.")

    # --- Run SUT ---
    print("\n--- Run SUT ---")
    run_script_file = config['run_script']
    run_script_path_abs = os.path.normpath(os.path.join(config['sut_abs_path'], run_script_file))
    run_interpreter = config.get('run_interpreter')
    run_args_str = config.get('run_args', '')

    if not run_script_file.strip():
        print("Error: No SUT run script specified (run_script is empty). Cannot proceed.", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(run_script_path_abs):
        print(f"Error: SUT run script '{run_script_file}' not found or is not a file at '{run_script_path_abs}'", file=sys.stderr)
        sys.exit(1)

    sut_command = []
    if run_interpreter:
        sut_command.append(run_interpreter)

    if not run_interpreter and os.name == 'posix':
        if not os.access(run_script_path_abs, os.X_OK):
            print(f"SUT run script {run_script_path_abs} is not executable. Attempting to make it executable...")
            try:
                os.chmod(run_script_path_abs, os.stat(run_script_path_abs).st_mode | 0o111)
            except Exception as e:
                print(f"Warning: Failed to make SUT run script executable: {e}. Execution might fail.", file=sys.stderr)
    sut_command.append(run_script_path_abs)

    if run_args_str:
        try:
            sut_command.extend(shlex.split(run_args_str))
        except Exception as e:
            print(f"Error splitting run_args '{run_args_str}': {e}", file=sys.stderr)
            sys.exit(1)

    print(f"Starting SUT: {run_script_file} with args: '{run_args_str}'")
    # print(f"Full command: {' '.join(sut_command)}") # For debugging
    print(f"SUT output will stream below. Press Ctrl+C to attempt to stop the SUT and this script.")

    run_command(sut_command, cwd=config['sut_abs_path'], check=True, capture_output_flag=False)

    print("SUT script execution finished.")

    print(f"\n--- SUT processing finished for: {sut_name} ---")

if __name__ == "__main__":
    main()
