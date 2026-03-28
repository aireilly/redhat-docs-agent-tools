---
name: verify-procedure
description: Execute, test, and verify AsciiDoc procedures on a live OpenShift or Kubernetes cluster. Runs every command and validates every YAML block against a real cluster. Use this skill whenever the user asks to verify a procedure, test documentation steps, run through a guided exercise, prove a procedure works, check if steps are correct on a live system, or do a dry run of a doc. Requires an active oc/kubectl connection. For static review without a live system, use docs-tools:technical-reviewer instead.
author: Red Hat Documentation Team
allowed-tools: Bash, Read, Edit, Glob, Grep
---

# Procedure Verification Skill

You execute documented OpenShift/Kubernetes procedures against a live cluster to prove they work end-to-end. **You** are the parser and judgment layer. The bash script `scripts/verify_proc.sh` is a thin executor — it only runs commands, validates YAML, and saves files.

**This is not a review tool.** For reviewing documentation quality without a live system, use `docs-tools:technical-reviewer`.

## Architecture: what you do vs. what the script does

| You (Claude) | Script (`verify_proc.sh`) |
|---|---|
| Read and parse the `.adoc` file | `init` — create workdir, detect oc/kubectl |
| Resolve `include::` directives by reading included files | `check-connection` — verify cluster login |
| Handle `ifdef::`/`ifndef::` conditionals intelligently | `execute <label> <command>` — run a command |
| Extract source blocks (understand nesting, listing blocks, callouts) | `validate-yaml <label> [file]` — YAML syntax + dry-run |
| Classify each block: execute, validate, save-to-file, skip (example output), skip (placeholders) | `validate-json <label>` — JSON syntax check |
| Strip prompt symbols from commands (`$`, `#`, `[root@host ~]#`) | `save-file <label> <path>` — write content to workdir |
| Detect backslash-continued lines and join them | `cleanup` — delete resources + workdir |
| Identify placeholders that need user substitution | `summary` — print pass/fail totals |
| Number steps hierarchically (1, 1.a, 1.b, 2.a.i) | |
| Flag suspicious patterns and undocumented assumptions | |
| Resolve AsciiDoc attributes (`{product-version}`, etc.) | |

## Profiles

A **profile** is an optional companion Markdown file that configures a verification run. Profiles live in the `profiles/` directory under this skill, organized by target repo and topic. They provide attribute values, placeholder substitutions, prerequisites, scope controls, assertions, and cleanup overrides — so procedures can be verified repeatably without interactive guidance.

See `profile-format.md` in this skill directory for the full format reference.

### Why profiles live here

Procedures live in external repositories like `openshift-docs` where you can only commit AsciiDoc source. Run configuration (substitution values, assertions, prerequisites) cannot be added there, so profiles live in this repo instead.

### Profile discovery

When the user invokes verify-procedure, look for a profile in this order:

1. **Explicit path**: user passes a profile file path (e.g., `--profile profiles/openshift-docs/networking/installing-ptp-operator.profile.md`)
2. **Auto-discovery**: search `profiles/` for a `.profile.md` file whose `procedure` frontmatter matches the `.adoc` path the user provided
3. **No profile**: run with default behavior (current behavior, unchanged)

If a profile is found, report it in the output header. If not, proceed silently — no profile is not an error.

### Profile loading

Read the profile file with the Read tool. Parse:

1. **YAML frontmatter** — extract `procedure`, `description`, `cluster`, `timeout`, `cleanup`
2. **## Attributes** — build an attribute map and conditional flags
3. **## Substitutions** — build a placeholder-to-value map
4. **## Prerequisites** — note assumed state (informational) and extract setup commands
5. **## Scope** — extract `mode`, `steps`, `skip` controls
6. **## Assertions** — build a step-label-to-assertion map
7. **## Cleanup** — extract preserve list and additional cleanup commands

Store all parsed profile data for use in subsequent steps.

## Workflow

### Step 0: Connectivity check

Before anything else, run:

```bash
bash scripts/verify_proc.sh init
bash scripts/verify_proc.sh check-connection
```

If a profile defines `timeout`, export it for the script:
```bash
export VERIFY_TIMEOUT=300
bash scripts/verify_proc.sh init
```

If the connection check fails and the profile `mode` is `execute` (or no profile), stop and tell the user to run `oc login` first, or suggest using `docs-tools:technical-reviewer` for offline review. If `mode` is `yaml-only`, continue without a cluster connection.

### Step 0.5: Run prerequisite setup (if profile provides it)

If the profile has `## Prerequisites` → `### Setup commands`, execute each command sequentially:

```bash
bash scripts/verify_proc.sh execute "prereq-1" "oc create namespace verify-test-ns --dry-run=client -o yaml | oc apply -f -"
```

If any setup command fails, stop the run and report which prerequisite could not be established. Include the profile's "Assumed state" items in the output header for context.

### Step 1: Parse the AsciiDoc file

Read the `.adoc` file with the Read tool. As you parse, do the following:

#### Handle include:: directives
When you encounter `include::path/to/file.adoc[leveloffset=...]`, read that file too and incorporate its content at the correct position. Resolve relative paths from the directory of the including file.

#### Handle ifdef/ifndef conditionals
Read the conditional and resolve it:
- If the profile defines conditional flags (e.g., `openshift-enterprise: yes`), use those — they take priority
- Otherwise, if the attribute is defined in the document or `_attributes.adoc`, evaluate it
- If neither source resolves it, note which branch you're taking and warn the user
- Do NOT silently skip content or mis-number steps

#### Extract source blocks
Identify `[source,TYPE]` blocks where TYPE is: `terminal`, `bash`, `shell`, `yaml`, `json`. Look for the `----` delimiters. Handle:
- **Nested blocks**: A source block inside an example block or sidebar — extract correctly
- **Listing blocks without [source]**: These are `----` delimited blocks without a source annotation — skip them (they're display-only)
- **Callout annotations**: Lines ending with `<1>`, `<2>`, etc. inside source blocks — strip these before execution

#### Resolve AsciiDoc attributes
If a block has `subs="attributes+"` or the document uses `{attribute-name}` references, resolve in this priority order:
1. **Profile attributes** — values from the profile's `## Attributes` table (highest priority)
2. **Document header** — `:attribute-name: value` in the `.adoc` file
3. **_attributes.adoc** — in the same directory or parent
4. **Cluster fallback** — for `{product-version}`, fall back to `oc version`

#### Classify each block

For each extracted source block, classify it as one of:

| Classification | Criteria | Action |
|---|---|---|
| **execute** | `[source,terminal]`, `[source,bash]`, `[source,shell]` block that contains actual commands | Strip prompts, join continued lines, send to `execute` |
| **validate-yaml** | `[source,yaml]` block | Pipe to `validate-yaml` |
| **validate-json** | `[source,json]` block | Pipe to `validate-json` |
| **save-to-file** | Step text says "save", "create a file named", "create a ... file" + mentions a filename | Pipe to `save-file` or `validate-yaml` with filename arg |
| **skip-example** | Block preceded by "Example output", "sample output", "expected output", "output resembles", "similar to the following" | Skip, report as `[SKIP]` |
| **skip-placeholder** | Block contains `<multi_word_placeholder>`, `${VAR}`, `CHANGEME`, `REPLACE`, or `<your-...>` patterns AND the profile does not provide substitution values for all of them | Skip, report with explanation |

#### Number steps hierarchically
Track AsciiDoc numbered list markers:
- `. Step text` → depth 1 (major step: 1, 2, 3)
- `.. Substep` → depth 2 (1.a, 1.b, 2.a)
- `... Sub-substep` → depth 3 (1.a.i, 1.a.ii)

Associate each source block with its nearest preceding step.

#### Apply substitutions (if profile provides them)

After classifying blocks but before execution, apply the profile's substitution map:

1. For each block classified as `skip-placeholder`, check if ALL placeholders in the block have substitution values in the profile
2. If yes, replace the placeholders with the profile values and reclassify the block as `execute`, `validate-yaml`, or `save-to-file` based on its source type
3. If only some placeholders are covered, keep the block as `skip-placeholder` and report which placeholders are still unresolved
4. Also apply substitutions to blocks classified as `execute` — they may contain placeholders mixed with real commands

Substitution matching rules:
- `<placeholder>` — match the literal angle-bracket string
- `${VAR}` and `$VAR` — match both forms
- `CHANGEME`, `REPLACE` — match as whole words only

#### Apply scope controls (if profile provides them)

After substitutions, filter the block list based on the profile's scope:

- **steps**: If set to a range (e.g., `1-5`) or list (e.g., `1,3,5`), only include blocks whose top-level step falls within the range. Default: `all`
- **skip**: Remove blocks with matching step labels. Report each as `[SKIP] <label> Skipped by profile`
- **mode**: If `dry-run-only`, reclassify `execute` blocks that contain `oc create` or `oc apply` (without `--dry-run`) as skip — only YAML validation and dry-runs proceed. If `yaml-only`, skip all execution and dry-runs, only check YAML/JSON syntax

### Step 2: Execute the procedure

Process blocks sequentially. For each block, based on its classification:

**execute** — Strip prompts and run:
```bash
bash scripts/verify_proc.sh execute "1.a" "oc get pods -n openshift-operators"
```

Prompt stripping rules (you apply these before sending to the script):
- `$ command` → `command`
- `# command` → `command`
- `[root@host ~]# command` → `command`
- `[user@host dir]$ command` → `command`
- `~]# command` → `command`

Join backslash-continued lines into a single command.

**validate-yaml** — Pipe the content via heredoc (handles quotes and special chars safely):
```bash
bash scripts/verify_proc.sh validate-yaml "1.a" <<'YAML'
apiVersion: v1
kind: Namespace
metadata:
  name: openshift-ptp
YAML
```

If the step instructs saving to a file, pass the filename:
```bash
bash scripts/verify_proc.sh validate-yaml "1.a" "my-resource.yaml" <<'YAML'
apiVersion: v1
kind: Namespace
metadata:
  name: openshift-ptp
YAML
```

**validate-json** — Pipe the content via heredoc:
```bash
bash scripts/verify_proc.sh validate-json "2" <<'JSON'
{"apiVersion": "v1", "kind": "ConfigMap"}
JSON
```

**save-to-file** — For non-YAML/JSON content that should be saved:
```bash
bash scripts/verify_proc.sh save-file "3.a" "config.conf" <<'CONTENT'
[defaults]
remote_user = ansible
CONTENT
```

**skip** — Just report it in your output, no script call needed.

#### Check assertions (if profile provides them)

After each step executes, check the profile's assertion table for matching step labels. For each assertion on that step:

| Type | Check |
|---|---|
| `contains` | stdout includes the expected string (case-sensitive) |
| `not-contains` | stdout does NOT include the string |
| `regex` | stdout matches the regex pattern |
| `exit-code` | command exited with the specified code |

Report assertion results:
- All pass: `[ASSERT] <label> All assertions passed (N/N)`
- Any fail: `[FAIL] <label> Assertion failed: expected output to contain "Succeeded", got "Pending"`

A step can have multiple assertions — all must pass for the step to be considered passing. Assertion failures override exit-code-based pass/fail (a step that exits 0 but fails an assertion is a FAIL).

Steps without assertions use the existing behavior (exit code 0 = pass).

### Step 3: Observations

After all blocks are processed, run:
```bash
bash scripts/verify_proc.sh summary
```

Then add your own observations:
- Steps that reference resources not created by earlier steps
- Missing `wait` or polling between create and verify steps
- Prerequisites that aren't documented
- Namespace assumptions
- Commands that would fail without prior `oc login` or specific permissions

### Step 4: Cleanup

Cleanup behavior depends on the profile's `cleanup` frontmatter value:

- **`auto`** — run cleanup immediately after summary
- **`manual`** (default) — only run when the user asks
- **`skip`** — do not clean up at all

When running cleanup:

```bash
bash scripts/verify_proc.sh cleanup
```

If the profile has a `## Cleanup` section:
- **Preserve list**: Before cleanup, note preserved resources. After `verify_proc.sh cleanup` runs, re-create any that were accidentally deleted, or filter them from the tracked resources before calling cleanup. Report preserved resources as `[PRESERVED] <resource>`
- **Additional commands**: After the standard cleanup, execute each additional cleanup command:
  ```bash
  bash scripts/verify_proc.sh execute "cleanup-1" "oc delete project verify-test-ns --ignore-not-found"
  ```

## Handling assemblies and partial cluster state

### Assemblies (multi-file procedures)
OpenShift docs use assemblies that `include::` multiple procedure modules. When verifying an assembly:
- Verify the full assembly end-to-end, not individual modules in isolation
- Resolve all `include::` directives to build the complete procedure before starting execution
- If the user points you at a single module (not an assembly), verify just that module but warn that it may depend on context from a parent assembly

### Partial cluster state
Procedures often assume prior setup (an operator installed, a namespace existing, a previous procedure completed). When a command fails because of missing prerequisites:
- Report the failure clearly: "Step 2 failed — namespace `openshift-ptp` does not exist. This procedure likely assumes the namespace was created by a prior procedure or prerequisite."
- Continue with remaining steps — later steps may still provide useful validation
- In your observations, list all assumed prerequisites you discovered during execution

## What you should flag (judgment calls only Claude can make)

- "Step 4 references namespace `openshift-ptp` but no earlier step creates it — is it expected to exist?"
- "Step 2 creates a resource and step 3 immediately queries it — may need a wait/retry"
- "The `oc adm` command in step 5 requires cluster-admin — not mentioned in prerequisites"
- "Step 3.b has `<your-registry-url>` — this is a placeholder, cannot execute"
- "The YAML in step 2 uses `apiVersion: v1beta1` which may be deprecated on this cluster version"
- "`ifdef::openshift-enterprise[]` — I'm including this block assuming an OpenShift Enterprise context"

## Output format

Present results as you go, using this format:

```
--- Procedure Verification: <filename> ---
Profile: installing-ptp-operator.profile.md (or "none")
Workdir: /tmp/verify-proc-XXXXXX
CLI: oc | Cluster: https://api.cluster.example.com:6443
Mode: execute | Timeout: 300s | Cleanup: auto
Assumed state: Cluster is reachable and user has cluster-admin

[Prereq 1] Setup: create test namespace
    Executing: oc create namespace verify-test-ns --dry-run=client -o yaml | oc apply -f -
    Result: PASS

[Step 1] Install the PTP Operator
  [Step 1.a] Save the following YAML as ptp-namespace.yaml:
    YAML syntax: PASS
    Saved to: /tmp/verify-proc-XXXXXX/ptp-namespace.yaml
    Dry-run: PASS
  [Step 1.b] Create the Namespace CR:
    Executing: oc create -f ptp-namespace.yaml
    Result: PASS
    [ASSERT] 1.b All assertions passed (1/1)

[Step 4] Verify the Operator is installed:
    Executing: oc get csv -n openshift-ptp
    Result: PASS
    Output: ptp-operator.v4.21.0  Succeeded
    [ASSERT] 4 All assertions passed (1/1)

--- Observations ---
- Step 3 applies a SubscriptionConfig but doesn't wait for the operator to become ready
  before step 4 checks the CSV. Consider adding: oc wait --for=condition=...
- No .Prerequisites section found — verify that prerequisites are documented

--- Summary ---
Total: 7 | Passed: 7 | Failed: 0 | Assertions: 2/2 passed
```
