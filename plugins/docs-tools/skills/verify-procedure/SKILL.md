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

## Workflow

### Step 0: Connectivity check

Before anything else, run:

```bash
bash scripts/verify_proc.sh init
bash scripts/verify_proc.sh check-connection
```

If the connection check fails, stop and tell the user to run `oc login` first, or suggest using `docs-tools:technical-reviewer` for offline review.

### Step 1: Parse the AsciiDoc file

Read the `.adoc` file with the Read tool. As you parse, do the following:

#### Handle include:: directives
When you encounter `include::path/to/file.adoc[leveloffset=...]`, read that file too and incorporate its content at the correct position. Resolve relative paths from the directory of the including file.

#### Handle ifdef/ifndef conditionals
Read the conditional and make a judgment call:
- If the attribute is defined in the document or `_attributes.adoc`, evaluate it
- If not, note which branch you're taking and warn the user
- Do NOT silently skip content or mis-number steps

#### Extract source blocks
Identify `[source,TYPE]` blocks where TYPE is: `terminal`, `bash`, `shell`, `yaml`, `json`. Look for the `----` delimiters. Handle:
- **Nested blocks**: A source block inside an example block or sidebar — extract correctly
- **Listing blocks without [source]**: These are `----` delimited blocks without a source annotation — skip them (they're display-only)
- **Callout annotations**: Lines ending with `<1>`, `<2>`, etc. inside source blocks — strip these before execution

#### Resolve AsciiDoc attributes
If a block has `subs="attributes+"` or the document uses `{attribute-name}` references:
1. Look for `:attribute-name: value` in the document header
2. Check for `_attributes.adoc` in the same directory or parent
3. For `{product-version}`, fall back to `oc version` on the cluster

#### Classify each block

For each extracted source block, classify it as one of:

| Classification | Criteria | Action |
|---|---|---|
| **execute** | `[source,terminal]`, `[source,bash]`, `[source,shell]` block that contains actual commands | Strip prompts, join continued lines, send to `execute` |
| **validate-yaml** | `[source,yaml]` block | Pipe to `validate-yaml` |
| **validate-json** | `[source,json]` block | Pipe to `validate-json` |
| **save-to-file** | Step text says "save", "create a file named", "create a ... file" + mentions a filename | Pipe to `save-file` or `validate-yaml` with filename arg |
| **skip-example** | Block preceded by "Example output", "sample output", "expected output", "output resembles", "similar to the following" | Skip, report as `[SKIP]` |
| **skip-placeholder** | Block contains `<multi_word_placeholder>`, `${VAR}`, `CHANGEME`, `REPLACE`, or `<your-...>` patterns | Skip, report with explanation |

#### Number steps hierarchically
Track AsciiDoc numbered list markers:
- `. Step text` → depth 1 (major step: 1, 2, 3)
- `.. Substep` → depth 2 (1.a, 1.b, 2.a)
- `... Sub-substep` → depth 3 (1.a.i, 1.a.ii)

Associate each source block with its nearest preceding step.

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

### Step 4: Cleanup (if requested)

Only run cleanup when the user asks or when invoked with cleanup intent:
```bash
bash scripts/verify_proc.sh cleanup
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
Workdir: /tmp/verify-proc-XXXXXX
CLI: oc | Cluster: https://api.cluster.example.com:6443

[Step 1] Install the PTP Operator
  [Step 1.a] Save the following YAML as ptp-namespace.yaml:
    YAML syntax: PASS
    Saved to: /tmp/verify-proc-XXXXXX/ptp-namespace.yaml
    Dry-run: PASS
  [Step 1.b] Create the Namespace CR:
    Executing: oc create -f ptp-namespace.yaml
    Result: PASS

[Step 4] Verify the Operator is installed:
    Executing: oc get csv -n openshift-ptp
    Result: PASS
    Output: ptp-operator.v4.21.0  Succeeded

--- Observations ---
- Step 3 applies a SubscriptionConfig but doesn't wait for the operator to become ready
  before step 4 checks the CSV. Consider adding: oc wait --for=condition=...
- No .Prerequisites section found — verify that prerequisites are documented

--- Summary ---
Total: 7 | Passed: 7 | Failed: 0
```
