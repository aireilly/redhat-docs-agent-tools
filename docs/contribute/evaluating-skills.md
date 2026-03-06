---
icon: lucide/flask-conical
---

# Evaluating skills

Use the [skill-creator](https://claude.com/plugins/skill-creator) Claude Code skill to test plugin commands and skills against defined test cases. This helps verify that commands produce consistent, expected output.

## Eval structure

Each plugin can include an `evals/` directory with test definitions:

```bash
plugins/my-plugin/
├── .claude-plugin/
│   └── plugin.json
├── commands/
│   └── my-command.md
├── evals/
│   └── evals.json
└── README.md
```

## Writing evals

Define test cases in `evals/evals.json`:

```json
{
  "skill_name": "my-plugin-command",
  "evals": [
    {
      "id": 0,
      "prompt": "/my-plugin:command",
      "expected_output": "Description of expected result",
      "files": [],
      "assertions": [
        {
          "name": "descriptive_assertion_name",
          "type": "contains",
          "value": "expected text in output"
        }
      ]
    }
  ]
}
```

### Assertion types

| Type | Description |
|------|-------------|
| `contains` | Output contains the specified value |
| `not_contains` | Output does not contain the specified value |

### Writing good assertions

- Give each assertion a descriptive `name` that reads clearly in results (e.g., `correct_greeting_format`, not `test1`)
- Focus assertions on what differentiates the skill from baseline behavior
- Assertions that pass both with and without the skill are "non-discriminating" — they don't prove the skill adds value
- For subjective outputs (writing style, tone), rely on qualitative review instead of assertions

## Running evals

Use the `skill-creator` skill to run and evaluate test cases:

```bash
/skill-creator test the <plugin-name> skill at plugins/<plugin-name>/commands/<command>.md
```

The skill-creator will:

1. Spawn parallel test runs — one **with** the skill and one **without** (baseline)
2. Grade each run against the assertions
3. Aggregate results into a benchmark
4. Generate an HTML viewer for qualitative review

### Eval workspace

Test outputs are written to a `<plugin-name>-workspace/` directory (gitignored by default). The workspace is organized by iteration:

```bash
my-plugin-workspace/
└── iteration-1/
    ├── test-case-name/
    │   ├── with_skill/
    │   │   └── outputs/
    │   ├── without_skill/
    │   │   └── outputs/
    │   └── eval_metadata.json
    ├── benchmark.json
    └── review.html
```

### Reviewing results

The generated `review.html` has two tabs:

- **Outputs** — browse each test case, compare with-skill vs. without-skill output, and leave feedback
- **Benchmark** — view pass rates, timing, and token usage across configurations

After reviewing, click **Submit All Reviews** to export `feedback.json`. Empty feedback means the output looked good.

## Iterating

If results need improvement, edit the skill and rerun. The skill-creator tracks iterations (`iteration-1/`, `iteration-2/`, etc.) and can show diffs between versions.

## Example: hello-world

The `hello-world` plugin includes a reference eval set at `plugins/hello-world/evals/evals.json` with three test cases:

| Test case | Prompt | Expected output |
|-----------|--------|----------------|
| No argument | `/hello-world:greet` | `Hello! Welcome to Red Hat Docs Agent Tools.` |
| With name | `/hello-world:greet Alice` | `Hello, Alice! Welcome to Red Hat Docs Agent Tools.` |
| Multi-word name | `/hello-world:greet Dr. Smith` | `Hello, Dr. Smith! Welcome to Red Hat Docs Agent Tools.` |

Run the example:

```bash
/skill-creator test the hello-world plugin's greet command at plugins/hello-world/commands/greet.md
```
