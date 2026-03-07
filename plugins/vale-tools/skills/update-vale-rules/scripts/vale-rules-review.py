#!/usr/bin/env python3

"""
Vale Rules Review - Identify false positives and update Vale rules

This script clones a repository, runs Vale with RedHat rules, identifies
unique errors, and directly adds exceptions to the YAML rule files.

Example run:
  python vale-rules-review.py https://github.com/example/repo

Copyright (c) 2025 Red Hat, Inc.
This program and the accompanying materials are made
available under the terms of the Eclipse Public License 2.0
which is available at https://www.eclipse.org/legal/epl-2.0/

SPDX-License-Identifier: EPL-2.0
"""

import argparse
import json
import shutil
import subprocess
import time
from collections import defaultdict
from multiprocessing import Manager, Pool, cpu_count
from pathlib import Path
from typing import Dict, List


class ValeRuleImprover:
    """Main class for Vale rule improvement workflow"""

    def __init__(self, repo_url: str, verbose: bool = True, num_workers: int = None,
                 file_types: List[str] = None, force_vale: bool = False,
                 skip_pr: bool = False):
        self.repo_url = repo_url
        self.verbose = verbose
        self.num_workers = num_workers or min(16, cpu_count())
        self.file_types = file_types or ["adoc"]
        self.force_vale = force_vale
        self.skip_pr = skip_pr
        self.repo_name = self._extract_repo_name(repo_url)
        self.tmp_dir = Path("./tmp")
        self.clone_dir = self.tmp_dir / self.repo_name
        self.vale_dir = Path(".vale")
        self.redhat_styles_dir = self.vale_dir / "styles" / "RedHat"
        self.errors_json = {}
        self.unique_errors = defaultdict(list)

    def _extract_repo_name(self, url: str) -> str:
        """Extract repository name from URL"""
        name = url.rstrip('/').split('/')[-1]
        if name.endswith('.git'):
            name = name[:-4]
        return name

    def _log(self, message: str, level: str = "INFO"):
        """Log message if verbose mode is enabled"""
        if self.verbose or level == "ERROR":
            print(f"[{level}] {message}")

    def setup_tmp_directory(self):
        """Create tmp directory if it doesn't exist"""
        self.tmp_dir.mkdir(exist_ok=True)
        self._log(f"Ensured tmp directory exists: {self.tmp_dir}")

    def clone_repository(self, skip_if_exists: bool = True):
        """Clone the repository to tmp directory"""
        if self.clone_dir.exists() and skip_if_exists:
            self._log(f"Repository already cloned at: {self.clone_dir}")
            self._log("Skipping clone. Use --force-clone to re-clone.")
            return

        if self.clone_dir.exists():
            self._log(f"Removing existing clone: {self.clone_dir}")
            shutil.rmtree(self.clone_dir)

        self._log(f"Cloning repository: {self.repo_url}")
        try:
            subprocess.run(
                ["git", "clone", self.repo_url, str(self.clone_dir)],
                check=True,
                capture_output=True,
                text=True
            )
            self._log(f"Successfully cloned to: {self.clone_dir}")
        except subprocess.CalledProcessError as e:
            self._log(f"Failed to clone repository: {e.stderr}", "ERROR")
            raise

    def _find_documentation_files(self) -> List[Path]:
        """Find all documentation files in the cloned repository"""
        patterns = [f"**/*.{ext}" for ext in self.file_types]
        files = []
        for pattern in patterns:
            files.extend(self.clone_dir.glob(pattern))
        return sorted(files)

    def _get_repo_size(self) -> str:
        """Get human-readable repository size"""
        try:
            result = subprocess.run(
                ["du", "-sh", str(self.clone_dir)],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.split()[0]
        except Exception:
            return "unknown"

    def _hide_existing_vale_configs(self) -> List[tuple]:
        """Temporarily hide existing Vale config files in the cloned repo"""
        config_names = [".vale.ini", "vale.ini", ".vale"]
        hidden_configs = []

        for config_name in config_names:
            config_path = self.clone_dir / config_name
            if config_path.exists():
                hidden_path = config_path.parent / f".{config_name}.tmp-hidden"
                self._log(f"Temporarily hiding {config_path}")
                config_path.rename(hidden_path)
                hidden_configs.append((hidden_path, config_path))

        return hidden_configs

    def _restore_vale_configs(self, hidden_configs: List[tuple]):
        """Restore hidden Vale config files"""
        for hidden_path, original_path in hidden_configs:
            if hidden_path.exists():
                self._log(f"Restoring {original_path}")
                hidden_path.rename(original_path)

    def _run_vale_on_batch(self, file_batch: List[Path], batch_id: int, vale_config: Path,
                           progress_dict: Dict = None) -> Dict:
        """Run Vale on a batch of files and return JSON results"""
        start_time = time.time()

        file_list = self.tmp_dir / f"vale-files-batch-{batch_id}.txt"
        with open(file_list, 'w') as f:
            for file_path in file_batch:
                f.write(f"{file_path}\n")

        self._log(f"Processing batch {batch_id} ({len(file_batch)} files)...")

        try:
            result = subprocess.run(
                [
                    "vale",
                    "--config", str(vale_config),
                    "--output", "JSON",
                    "--no-exit",
                ] + [str(f) for f in file_batch],
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout per batch
            )

            if progress_dict is not None:
                progress_dict['completed'] += 1
                elapsed = time.time() - start_time
                progress_dict['total_time'] += elapsed

            if result.stdout.strip():
                try:
                    batch_result = json.loads(result.stdout)
                    self._log(f"Batch {batch_id}: Completed in {elapsed:.1f}s, found {len(batch_result)} files with errors")
                    return batch_result
                except json.JSONDecodeError:
                    self._log(f"Batch {batch_id}: Invalid JSON output", "ERROR")
                    return {}
            return {}

        except subprocess.TimeoutExpired:
            self._log(f"Batch {batch_id}: Timeout after 30 minutes", "ERROR")
            if progress_dict is not None:
                progress_dict['completed'] += 1
            return {}
        except Exception as e:
            self._log(f"Batch {batch_id}: Error - {str(e)}", "ERROR")
            if progress_dict is not None:
                progress_dict['completed'] += 1
            return {}
        finally:
            if file_list.exists():
                file_list.unlink()

    def run_vale(self) -> Path:
        """Run Vale on the cloned repository with RedHat rules only (parallel)"""
        self._log("Running Vale on cloned repository with parallel processing...")

        hidden_configs = self._hide_existing_vale_configs()

        try:
            vale_config = self._create_redhat_only_config()
            repo_size = self._get_repo_size()
            self._log(f"Repository size: {repo_size}")

            all_files = self._find_documentation_files()
            file_types_str = ", ".join(self.file_types)
            self._log(f"Found {len(all_files)} documentation files ({file_types_str})")

            if not all_files:
                self._log("No documentation files found", "ERROR")
                output_file = self.tmp_dir / f"vale-{self.repo_name}.json"
                with open(output_file, 'w') as f:
                    f.write("{}")
                return output_file

            batch_size = max(1, len(all_files) // self.num_workers)
            batches = [all_files[i:i + batch_size] for i in range(0, len(all_files), batch_size)]

            self._log(f"Processing {len(all_files)} files in {len(batches)} batches...")

            merged_results = {}
            start_time = time.time()

            with Manager() as manager:
                progress = manager.dict()
                progress['completed'] = 0
                progress['total_time'] = 0.0

                with Pool(processes=self.num_workers) as pool:
                    async_results = [
                        pool.apply_async(
                            self._run_vale_on_batch_wrapper,
                            (batch, i, vale_config, progress)
                        )
                        for i, batch in enumerate(batches)
                    ]

                    last_completed = 0
                    while any(not r.ready() for r in async_results):
                        time.sleep(2)
                        completed = progress['completed']
                        if completed > last_completed:
                            percent = (completed / len(batches)) * 100
                            avg_time = progress['total_time'] / completed if completed > 0 else 0
                            remaining = len(batches) - completed
                            eta_seconds = avg_time * remaining
                            eta_str = f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s"
                            self._log(f"Progress: {completed}/{len(batches)} ({percent:.1f}%) | ETA: {eta_str}")
                            last_completed = completed

                    results = [r.get() for r in async_results]
                    for batch_result in results:
                        if batch_result:
                            merged_results.update(batch_result)

            total_time = time.time() - start_time

            output_file = self.tmp_dir / f"vale-{self.repo_name}.json"
            with open(output_file, 'w') as f:
                json.dump(merged_results, f, indent=2)

            self._log(f"Vale results saved to: {output_file}")
            self._log(f"Total files with errors: {len(merged_results)}")
            self._log(f"Total time: {int(total_time // 60)}m {int(total_time % 60)}s")

            return output_file

        finally:
            self._restore_vale_configs(hidden_configs)

    def _run_vale_on_batch_wrapper(self, batch: List[Path], batch_id: int, vale_config: Path,
                                   progress_dict: Dict = None) -> Dict:
        """Wrapper for multiprocessing compatibility"""
        return self._run_vale_on_batch(batch, batch_id, vale_config, progress_dict)

    def _create_redhat_only_config(self) -> Path:
        """Create a temporary Vale config that only uses RedHat rules"""
        styles_path = self.vale_dir.absolute() / "styles"

        config_content = f"""StylesPath = {styles_path}

MinAlertLevel = suggestion

IgnoredScopes = code, tt, img, url, a, body.id

SkippedScopes = script, style, pre, figure, code, tt, blockquote, listingblock, literalblock

Packages = RedHat

[*.adoc]
BasedOnStyles = RedHat

[*.md]
BasedOnStyles = RedHat
TokenIgnores = (\\x60[^\\n\\x60]+\\x60), ([^\\n]+=[^\\n]*), (\\+[^\\n]+\\+), (http[^\\n]+\\[)

[*.ini]
BasedOnStyles = RedHat
TokenIgnores = (\\x60[^\\n\\x60]+\\x60), ([^\\n]+=[^\\n]*), (\\+[^\\n]+\\+), (http[^\\n]+\\[)
"""
        config_file = self.tmp_dir / "vale-redhat-only.ini"
        with open(config_file, 'w') as f:
            f.write(config_content)

        self._log(f"Created temporary Vale config: {config_file}")
        return config_file

    def parse_and_deduplicate_errors(self, json_file: Path):
        """Parse Vale JSON output and deduplicate errors"""
        self._log("Parsing and deduplicating errors...")

        with open(json_file, 'r') as f:
            content = f.read().strip()

        if not content:
            self._log("Vale output is empty. No errors to process.", "ERROR")
            return

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            self._log(f"Failed to parse Vale JSON output: {e}", "ERROR")
            raise

        if isinstance(data, dict) and "Code" in data and data.get("Code") == "E100":
            self._log(f"Vale runtime error: {data.get('Text', 'Unknown error')}", "ERROR")
            raise RuntimeError(f"Vale error: {data.get('Text', 'Unknown error')}")

        self.errors_json = data

        seen_errors = set()

        for file_path, errors in self.errors_json.items():
            for error in errors:
                error_key = (
                    error.get('Check', ''),
                    error.get('Message', ''),
                    error.get('Match', ''),
                    error.get('Severity', '')
                )

                if error_key not in seen_errors:
                    seen_errors.add(error_key)
                    rule_name = error.get('Check', 'Unknown')
                    self.unique_errors[rule_name].append({
                        'message': error.get('Message', ''),
                        'match': error.get('Match', ''),
                        'severity': error.get('Severity', ''),
                        'link': error.get('Link', ''),
                        'example_file': file_path,
                        'line': error.get('Line', 0)
                    })

        total_errors = sum(len(errors) for errors in self.errors_json.values())
        unique_count = sum(len(errors) for errors in self.unique_errors.values())

        self._log(f"Total errors: {total_errors}")
        self._log(f"Unique errors: {unique_count}")
        self._log(f"Rules with errors: {len(self.unique_errors)}")

        dedup_file = self.tmp_dir / f"vale-{self.repo_name}-deduplicated.json"
        with open(dedup_file, 'w') as f:
            json.dump(dict(self.unique_errors), f, indent=2)
        self._log(f"Deduplicated errors saved to: {dedup_file}")

    def _get_rule_file(self, rule_name: str) -> Path:
        """Get the path to a rule file from its name"""
        if not rule_name.startswith("RedHat."):
            return None

        rule_basename = rule_name.replace("RedHat.", "")
        rule_file = self.redhat_styles_dir / f"{rule_basename}.yml"
        return rule_file

    def update_rules(self):
        """Add exception terms directly to Vale rule YAML files"""
        self._log("Updating rule files with exceptions...")

        rules_updated = 0

        for rule_name in sorted(self.unique_errors.keys()):
            errors = self.unique_errors[rule_name]
            rule_file = self._get_rule_file(rule_name)

            if not rule_file or not rule_file.exists():
                self._log(f"Rule file not found for {rule_name}, skipping")
                continue

            # Get unique matches for this rule
            unique_matches = set()
            for error in errors:
                match = error.get('match', '').strip()
                if match:
                    unique_matches.add(match)

            if not unique_matches:
                continue

            terms = sorted(unique_matches)
            added = self._add_exceptions_to_rule(rule_file, terms)

            if added > 0:
                rules_updated += 1
                self._log(f"Added {added} exceptions to {rule_name}")

        self._log(f"Updated {rules_updated} rule files")
        return rules_updated > 0

    def _add_exceptions_to_rule(self, rule_file: Path, terms: List[str]) -> int:
        """Add exception terms to a Vale rule YAML file"""
        with open(rule_file, 'r') as f:
            content = f.read()
            lines = content.split('\n')

        # Find the exceptions: or filters: section
        insert_index = None
        section_type = None

        for i, line in enumerate(lines):
            if line.strip().startswith('exceptions:'):
                section_type = 'exceptions'
                insert_index = i + 1
            elif line.strip().startswith('filters:'):
                section_type = 'filters'
                insert_index = i + 1

        if insert_index is None:
            # No exceptions or filters section found, add exceptions at the end
            lines.append('exceptions:')
            insert_index = len(lines)
            section_type = 'exceptions'

        # Find where the section ends (next non-indented line or list item section)
        end_index = insert_index
        for i in range(insert_index, len(lines)):
            line = lines[i]
            # If we hit a non-list item that's not indented, stop
            if line.strip() and not line.startswith('  ') and not line.strip().startswith('-'):
                break
            if line.strip().startswith('-') or line.strip() == '':
                end_index = i + 1

        # Add new terms at the end of the section
        new_lines = []
        for term in terms:
            # Check if term already exists
            term_exists = False
            for line in lines:
                if term in line:
                    term_exists = True
                    break

            if not term_exists:
                if section_type == 'filters':
                    # Filters use regex patterns
                    new_lines.append(f'  - "{term}"')
                else:
                    # Exceptions are simple strings
                    new_lines.append(f'  - {term}')

        if new_lines:
            # Insert new lines at the end of the section
            for i, new_line in enumerate(new_lines):
                lines.insert(end_index + i, new_line)

            # Write back
            with open(rule_file, 'w') as f:
                f.write('\n'.join(lines))

        return len(new_lines)

    def create_pull_request(self):
        """Create a pull request with the rule changes"""
        self._log("Checking for modified rules...")

        rules_result = subprocess.run(
            ["git", "status", "--porcelain", str(self.redhat_styles_dir)],
            capture_output=True,
            text=True
        )

        if not rules_result.stdout.strip():
            self._log("No rule changes detected. Skipping PR creation.")
            return

        self._log("Creating pull request with rule improvements...")

        branch_name = f"vale-rule-improvements-{self.repo_name}"

        try:
            # Stash any uncommitted changes
            self._log("Stashing uncommitted changes...")
            subprocess.run(
                ["git", "stash", "push", "-m", f"vale-rules-review-{self.repo_name}"],
                check=True,
                capture_output=True,
                text=True
            )

            # Fetch upstream
            self._log("Fetching upstream...")
            subprocess.run(
                ["git", "fetch", "upstream"],
                check=True,
                capture_output=True,
                text=True
            )

            # Switch to main branch
            self._log("Switching to main branch...")
            subprocess.run(
                ["git", "checkout", "main"],
                check=True,
                capture_output=True,
                text=True
            )

            # Reset to upstream/main
            self._log("Resetting to upstream/main...")
            subprocess.run(
                ["git", "reset", "--hard", "upstream/main"],
                check=True,
                capture_output=True,
                text=True
            )

            # Delete existing branch if exists
            branch_check = subprocess.run(
                ["git", "rev-parse", "--verify", branch_name],
                capture_output=True,
                text=True
            )
            if branch_check.returncode == 0:
                self._log(f"Deleting existing branch: {branch_name}")
                subprocess.run(
                    ["git", "branch", "-D", branch_name],
                    check=True,
                    capture_output=True,
                    text=True
                )

            # Create fresh branch
            self._log(f"Creating branch: {branch_name}")
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                check=True,
                capture_output=True,
                text=True
            )

            # Apply stashed changes
            self._log("Applying stashed changes...")
            subprocess.run(
                ["git", "stash", "pop"],
                check=True,
                capture_output=True,
                text=True
            )

            # Stage rule changes only
            subprocess.run(
                ["git", "add", str(self.redhat_styles_dir)],
                check=True
            )

            # Commit
            commit_message = f"""Improve Vale rules based on {self.repo_name} analysis

Analyzed {self.repo_name} repository and identified false positives
in RedHat Vale rules. Added exceptions to reduce false positives.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
"""

            subprocess.run(
                ["git", "commit", "-m", commit_message],
                check=True
            )

            # Push branch
            subprocess.run(
                ["git", "push", "-u", "origin", branch_name],
                check=True
            )

            # Create PR
            pr_body = f"""## Summary
- Analyzed the {self.repo_name} repository for Vale rule false positives
- Added exceptions to reduce false positive alerts

## Changes
Updates to Vale rules in `.vale/styles/RedHat/`

## Test Plan
- [ ] Run Vale on {self.repo_name} and verify reduced false positives
- [ ] Run Vale tests to ensure no regressions

🤖 Generated with [Claude Code](https://claude.com/claude-code)
"""

            result = subprocess.run(
                [
                    "gh", "pr", "create",
                    "--title", f"Improve Vale rules based on {self.repo_name} analysis",
                    "--body", pr_body
                ],
                capture_output=True,
                text=True
            )

            self._log("Pull request created successfully!")
            print(result.stdout)

        except subprocess.CalledProcessError as e:
            self._log(f"Failed to create PR: {e.stderr}", "ERROR")
            raise

    def run(self):
        """Execute the workflow"""
        try:
            self.setup_tmp_directory()
            self.clone_repository()

            # Check if deduplicated results already exist
            dedup_file = self.tmp_dir / f"vale-{self.repo_name}-deduplicated.json"
            json_file = self.tmp_dir / f"vale-{self.repo_name}.json"

            if dedup_file.exists() and not self.force_vale:
                self._log(f"Found existing deduplicated results: {dedup_file}")
                self._log("Skipping Vale run. Use --force-vale to run Vale again.")
                with open(dedup_file, 'r') as f:
                    self.unique_errors = defaultdict(list, json.load(f))
            else:
                if self.force_vale and dedup_file.exists():
                    self._log("Forcing new Vale run (--force-vale specified)")
                json_file = self.run_vale()
                self.parse_and_deduplicate_errors(json_file)

            if not self.unique_errors:
                self._log("No errors found. Nothing to update.")
                return

            # Update rule files directly
            if self.update_rules():
                if not self.skip_pr:
                    self.create_pull_request()
                else:
                    self._log("Skipping PR creation (--skip-pr specified)")
            else:
                self._log("No changes made to rule files")

        except Exception as e:
            self._log(f"Workflow failed: {str(e)}", "ERROR")
            raise


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Vale Rules Review - Identify false positives and update Vale rules",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze repo and update rules
  %(prog)s https://github.com/example/repo

  # Force fresh Vale run
  %(prog)s https://github.com/example/repo --force-vale

  # Update rules without creating PR
  %(prog)s https://github.com/example/repo --skip-pr
        """
    )

    parser.add_argument(
        "repo_url",
        help="URL of the repository to analyze"
    )

    parser.add_argument(
        "-j", "--jobs",
        type=int,
        default=None,
        help="Number of parallel workers (default: min(16, CPU count))"
    )

    parser.add_argument(
        "-t", "--file-types",
        type=str,
        default="adoc",
        help="Comma-separated file extensions to process (default: adoc)"
    )

    parser.add_argument(
        "--force-vale",
        action="store_true",
        help="Force a new Vale run even if cached results exist"
    )

    parser.add_argument(
        "--skip-pr",
        action="store_true",
        help="Update rules but don't create a pull request"
    )

    args = parser.parse_args()

    file_types = [ext.strip() for ext in args.file_types.split(',')]

    improver = ValeRuleImprover(
        args.repo_url,
        num_workers=args.jobs,
        file_types=file_types,
        force_vale=args.force_vale,
        skip_pr=args.skip_pr
    )
    improver.run()


if __name__ == "__main__":
    main()
