---
name: verify-procedure
description: Execute and test AsciiDoc procedures on a live system. Runs every command and validates every YAML block against a real cluster, VM, or host. Requires an active connection to the target system. For static review without a live system, use the docs-tools:technical-reviewer agent instead.
author: Red Hat Documentation Team
allowed-tools: Bash, Read, Edit, Glob
---

# Procedure Verification Skill

This skill executes documented procedures against a live system to prove they work end-to-end. It is the "guided exercise tester" — it runs every command, applies every YAML block, and reports what passes and what breaks.

**This is not a review tool.** For reviewing documentation quality, prerequisites, and structure without a live system, use the `docs-tools:technical-reviewer` agent.

## Prerequisites

You must be connected to the target system before invoking this skill:

- **OpenShift/Kubernetes**: `oc login` or valid `~/.kube/config`
- **RHEL/Linux**: Local access or SSH session to the target host
- **Ansible**: `ansible --version` succeeds and inventory is accessible

At invocation, the skill runs a connectivity check (e.g., `oc whoami`). If the check fails, the skill exits and directs the user to log in first or use `docs-tools:technical-reviewer` for offline review.

## How it works

1. **Parse**: Read the `.adoc` file and extract all `[source,terminal]`, `[source,bash]`, `[source,yaml]`, and `[source,json]` blocks, associating each with its numbered step.
2. **Execute**: Run the `verify_proc.rb` script against the file:
   ```bash
   ruby <skill_dir>/scripts/verify_proc.rb <file.adoc>
   ruby <skill_dir>/scripts/verify_proc.rb --cleanup <file.adoc>
   ```
3. **Report**: Present the script output and flag any additional observations.

## What the Ruby script does

The `scripts/verify_proc.rb` script is a procedure runner that processes an AsciiDoc file sequentially:

### Working directory

Creates a temporary working directory (`/tmp/verify-proc-*`) for each run. All YAML files referenced in the procedure are saved here, and all bash commands execute with this as their working directory. This ensures:
- Relative file paths in commands (e.g., `oc create -f foo.yaml`) resolve correctly
- The user's working directory is not polluted with temporary files
- Each run is isolated from previous runs

### Step extraction with hierarchical numbering

- Parses AsciiDoc numbered steps (`. Step text`, `.. Substep`, `... Sub-substep`) and tracks depth
- Associates each source block with its parent step
- Uses hierarchical step labels: `1`, `1.a`, `1.b`, `2.a.i` instead of flat sequential numbers
- This makes it easy to correlate script output with the actual procedure structure

### Save-YAML-to-file linking

Detects the common documentation pattern where a YAML block is preceded by a step like:

```
.. Save the following YAML in the `foo.yaml` file:
```

When this pattern is detected:
1. The YAML is validated for syntax
2. The YAML is written to `<workdir>/foo.yaml`
3. Subsequent commands like `oc create -f foo.yaml` find the file and execute successfully

Filename extraction matches backtick-quoted filenames (`` `foo.yaml` ``) or bare `.yaml`/`.yml` filenames in the step text.

### Smart skipping

- **Example output blocks**: Detects blocks preceded by "Example output", "sample output", "expected output", or "output is shown" and skips them
- **Placeholder blocks**: Detects `<multi_word_placeholder>` patterns, `${VAR}` syntax, `CHANGEME`, or `REPLACE` markers and skips those steps

### AsciiDoc attribute resolution

When a source block has `subs="attributes+"`, the script resolves common AsciiDoc attributes before validation or execution:

- `{product-version}` → detected from the live cluster via `oc version`
- `{product-title}` → `OpenShift Container Platform`
- `{op-system-base}` → `RHEL`
- `{op-system}` → `RHCOS`

This prevents false YAML validation failures on blocks that contain attribute placeholders.

### YAML validation

- Parses every `[source,yaml]` block with Ruby's YAML parser for syntax errors
- If the YAML contains `apiVersion:` (Kubernetes resource), runs `oc apply --dry-run=client` or `kubectl apply --dry-run=client` (auto-detects which CLI is available)
- Reports `[VALID]` or `[FAILURE]` with the specific error

### JSON validation

- Parses `[source,json]` blocks with Ruby's JSON parser for syntax errors
- Reports `[VALID]` or `[FAILURE]`

### Bash execution

- Strips leading `$ ` prompts from command lines
- Joins backslash-continued lines
- Executes each command via `Open3.capture3` in the working directory
- For verification steps (containing words like "verify", "check", "confirm"), displays the command output
- On failure, logs the error but continues to the next step

### Best practices check

- Scans the full file for login/setup patterns (`oc login`, `ssh`, `sudo`, `subscription-manager`, `dnf install`, `ansible-playbook`, etc.)
- Warns if no setup pattern is found in a procedure over 500 characters, suggesting potential "magic steps"

### Resource tracking and cleanup

The script tracks resources created during verification:
- Records `oc create -f` / `oc apply -f` commands and their file paths
- Captures resource identifiers from stdout (e.g., `namespace/openshift-ptp created`)

When invoked with `--cleanup`:
- Deletes tracked resources in reverse order (last created, first deleted)
- Uses `--ignore-not-found` to handle partially-created resources gracefully
- Removes the temporary working directory

Without `--cleanup`, the working directory and resources are retained so the user can inspect them.

### Summary

- Reports total executable steps, pass count, and fail count
- Uses hierarchical step labels matching the procedure structure
- Lists each failed step with its error message
- Flags if no verification step exists in the procedure

## Output format

The script produces structured terminal output:

```
--- Starting Procedure Validation: <file.adoc> ---
[INFO] Working directory: /tmp/verify-proc-abc123

[Step 1] Create a namespace for the PTP Operator.

[Step 1.a] Save the following YAML in the `ptp-namespace.yaml` file:
[VALID] YAML syntax for Step 1.a is correct.
[INFO] Saved YAML to /tmp/verify-proc-abc123/ptp-namespace.yaml
[VALID] Resource logic (dry-run via oc) passed for Step 1.a.

[Step 1.b] Create the `Namespace` CR:
Executing: oc create -f ptp-namespace.yaml
[SUCCESS] Step 1.b executed.

[Step 4] To verify that the Operator is installed, enter the following command:
Executing: oc get csv -n openshift-ptp -o custom-columns=...
[SUCCESS] Step 4 executed.
Output: Name                         Phase
ptp-operator.v4.21.0-...     Succeeded
-> Verification successfully performed.

[Step 4] To verify that the Operator is installed, enter the following command:
[SKIP] Example output - not executed

============================================================
FINAL SUMMARY
============================================================
Total executable steps: 7
Passed: 7
Failed: 0
============================================================
✓ All steps PASSED
============================================================

[INFO] Working directory retained at: /tmp/verify-proc-abc123
[INFO] Run with --cleanup to auto-delete resources and working directory after verification.
```

After the script output, add observations about any patterns noticed during execution (timing issues, missing waits, ordering problems).
