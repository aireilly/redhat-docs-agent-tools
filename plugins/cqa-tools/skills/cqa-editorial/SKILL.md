---
name: cqa-editorial
description: Use when assessing CQA parameters P13-P14, Q1-Q5, Q18, Q20 (editorial quality). Checks grammar, content types, readability, scannability, fluff, style guide compliance, and tone.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# CQA P13-P14, Q1-Q5, Q18, Q20: Editorial Quality

## Parameters

| # | Parameter | Level |
|---|-----------|-------|
| P13 | Grammatically correct American English | Required |
| P14 | Correct content type matches actual content | Required |
| Q1 | Scannable: sentences <= 22 words avg, paragraphs 2-3 sentences | Required |
| Q2 | Clearly written and understandable | Important |
| Q3 | Simple words (no "utilize", "leverage", "in order to") | Important |
| Q4 | Readability score (11-12th grade level) | Important |
| Q5 | No fluff ("This section describes...", "as mentioned") | Important |
| Q18 | Content follows Red Hat style guide | Required |
| Q20 | Appropriate conversational tone (2nd person, professional) | Important |

## Directory note

Some repos use `modules/` instead of `topics/` for content files. All `topics/` references in this skill apply equally to `modules/`. The automation scripts accept `--scan-dirs` to override the default scan directories.

## Checks

### P13: Grammar

- American English spelling
- No grammatical errors in titles or body text
- Correct article usage ("a" vs "an")

### P14: Content type

- `:_mod-docs-content-type:` matches actual content
- Filename prefix matches content type
- Procedures have `.Procedure` with ordered list
- Concepts have explanatory content, no `.Procedure`

### Q1: Scannability

#### Thresholds

| Metric | Target | Hard limit |
|--------|--------|------------|
| Sentence length | <= 22 words average | Flag sentences > 30 words |
| Paragraph length | 2-3 sentences | Flag paragraphs > 4 sentences |
| Lists | Use bulleted lists for 3+ items | Flag inline enumerations |

#### What counts as prose (check these)

Only check actual prose text in `topics/` and `assemblies/` files:

- Abstract paragraphs (text after `[role="_abstract"]`)
- Body paragraphs between structural markers
- Prose within admonition blocks (NOTE, WARNING, IMPORTANT, TIP, CAUTION)
- Prose portion of bullet/ordered list items (the text after `* ` or `. `)
- Introductory text in assemblies (before first `include::`)

#### What to skip (not prose)

- Code/literal/passthrough blocks (between `----`, `....`, `++++` delimiters)
- AsciiDoc metadata, attributes (`:attr:` lines), directives (`include::`, `image::`, `ifdef::`)
- Block titles (`.Example`, `.Procedure`, `.Prerequisites`)
- Table content (lines starting with `|`, `|===` delimiters)
- Definition list terms (`term::` entries) — the term itself is not a sentence
- Block attribute annotations (`[source,yaml]`, `[role="_abstract"]`, `[id="..."]`)
- Comments (`// ...`)
- Headings (`= `, `== `)
- List continuation markers (`+` on its own line)
- URL-only list items (`* xref:...[]`, `* link:...[]`)

#### Word counting

- AsciiDoc attributes (`{prod-short}`, `{orch-name}`) count as the number of words they resolve to
- Backtick literals (`\`command\``) count as 1 word regardless of content
- Link macros: count only the link text, not the URL
- Leading list markers (`* `, `. `, `.. `) are not words

#### How to assess sentence length

Read each prose paragraph in every file in `topics/` and `assemblies/`. For each paragraph:

1. Split into sentences (split on `. ` followed by uppercase, `? `, `! `)
2. Count words per sentence (using word counting rules above)
3. Flag any sentence over 30 words
4. Note the file's average sentence length

Each list item is an independent unit — do not concatenate consecutive list items into a single "paragraph."

#### Sentence splitting patterns

When a sentence exceeds 30 words, split it using these patterns:

| Pattern | Split point | Example |
|---------|-------------|---------|
| "..., so that..." | Split at ", so that" | "Configure X. This allows Y." |
| "..., as..." (causal) | Split at ", as" | "X happens. The reason is Y." |
| "..., which..." (non-restrictive) | Split at ", which" | "X does Y. It also does Z." |
| "... to ... to ..." (chained infinitives) | Split after first purpose | "Do X. This enables Y." |
| "..., or ..." (alternative actions) | Split at ", or" | "Do X. Alternatively, do Y." |
| Inline enumeration | Convert to bulleted list | `The supported values are:\n* X\n* Y\n* Z` |
| Abstract with WHAT + WHY | Split into two sentences | "Do X to achieve Y." → "Do X. This achieves Y." |

#### How to assess paragraph length

A paragraph is a block of consecutive prose lines separated by blank lines. For each paragraph:

1. Count the number of sentences
2. Flag paragraphs with more than 4 sentences
3. Split long paragraphs at logical topic shifts by inserting a blank line

#### False positives to ignore

These patterns look like long sentences/paragraphs but are structured content:

| Pattern | Why it's not a scannability issue |
|---------|-----------------------------------|
| Definition list entries (`term:: description`) | Renders as formatted key-value pairs, not prose |
| Consecutive bullet items (`* item1\n* item2\n* item3`) | Each item is independent; they are not one paragraph |
| Procedure sub-steps (`.. step1\n.. step2`) | Ordered sub-steps render as a nested list |
| CSV-like metric tables | Renders as structured data |
| Code block annotations with backtick-heavy content | Technical identifiers inflate word count |
| Link-heavy sentences (URLs inside `link:...[text]`) | URLs inflate raw character/word count |

#### Bulleted lists

Check for inline enumerations that would be more scannable as lists:

- Flag: "The supported values are X, Y, and Z." (3+ items in a sentence)
- Fix: Convert to a bulleted list with a lead-in sentence
- Exception: Short enumerations of 2 items are fine inline ("supports X and Y")

#### Graphics and diagrams

Verify that complex procedures and architectural concepts have supporting diagrams:

- Architecture overviews should have component diagrams
- Monitoring/metrics topics should have dashboard screenshots
- Multi-step workflows with branching logic should have flow diagrams
- Simple configuration procedures do not need diagrams

#### Scoring

| Score | Criteria |
|-------|----------|
| **4** | 0 prose sentences > 30 words, overall avg <= 22 words/sentence, no paragraphs > 4 sentences, lists used for enumerations, graphics where needed |
| **3** | 1-5 sentences > 30 words (borderline cases like 31-33 words), avg <= 22, minor paragraph length issues |
| **2** | Multiple sentences > 30 words, avg > 22 in several files, long paragraphs common |
| **1** | Scannability not assessed or widespread issues |

### Q2: Clearly written

#### Core criteria

- Content is understandable on first read
- Technical terms are defined or linked at first use
- Cause-and-effect relationships are explicit
- Transitions between topics are logical

#### Minimalism principles

Minimalism focuses documentation on readers' needs through five principles:

1. **Customer focus and action orientation** — Know what users do and why. Minimize content between the user and real work. Separate conceptual information from procedural tasks.
2. **Findability** — Content is findable through search and scannable (short paragraphs, sentences, bulleted lists). See Q1 for detailed scannability checks.
3. **Titles and headings** — Clear titles with familiar keywords. Keep titles between 3-11 words. Too short = lacks clarity. Too long = poor search visibility. See title length checks below.
4. **Elimination of fluff** — No long introductions or unnecessary context. See Q5 for detailed fluff checks.
5. **Error recovery, verification, troubleshooting** — Procedures include verification steps and troubleshooting where appropriate.

#### Title length checks

For each file in `topics/` and `assemblies/`, check the main title (`= `) and subsection headings (`== `):

| Metric | Target | Flag |
|--------|--------|------|
| Word count | 3-11 words (resolved) | Flag titles under 3 words or over 11 words |
| Character count | 50-80 characters (resolved) | Titles under 50 chars acceptable if clear. Flag titles over 80 chars |

**Attribute resolution for word counting:**
- `{prod-short}` = 3 words, `{prod}` = 5 words, `{ocp}` = 3 words
- `{orch-name}` = 1 word, `{devworkspace}` = 2 words
- Backtick-quoted strings = 1 word each

**When fixing long titles:** Use shorter attribute forms (`{prod-short}` instead of `{prod}`, `{orch-name}` instead of `{ocp}`) to reduce word/character count while preserving meaning.

**Acceptable exceptions:** Single Kubernetes resource names as subsection headings in reference/concept files (e.g., `== DevWorkspaceTemplate`) are acceptable when the parent section provides context. Two-word titles like "Server components" or "Creating workspaces" are acceptable if clear and descriptive.

#### User pronoun rules

- **Animate users** (persons, human accounts): use "who" — "users who want to configure..."
- **Inanimate entities** (system accounts, user mappings, roles): use "that" — "a Linux user account that has restricted access...", "an SELinux user mapping that restricts..."
- **Ambiguous relative clauses**: When "that" could refer to either an inanimate object or an animate user, restructure the sentence to eliminate ambiguity

#### Verification section coverage

- Procedures with observable outcomes should have `.Verification` sections
- Simple procedures with self-evident outcomes (UI navigation, single configuration edits) can omit verification
- No procedure should have verification steps as the last step inside `.Procedure` — use a separate `.Verification` section

#### Scoring

| Score | Criteria |
|-------|----------|
| **4** | Content understandable on first read, all minimalism principles applied, titles 3-11 words, correct pronoun usage, verification sections where meaningful |
| **3** | Minor clarity issues (1-3 ambiguous sentences), a few titles outside range, minor pronoun issues |
| **2** | Multiple clarity issues, minimalism principles not consistently applied, many short/long titles |
| **1** | Content frequently unclear, minimalism not applied |

### Q3: Simple words

Flag and replace:

- "utilize" -> "use"
- "leverage" -> "use"
- "in order to" -> "to"
- "prior to" -> "before"
- "subsequent to" -> "after"
- "commence" -> "start" or "begin"
- "terminate" -> "stop" or "end"
- "facilitate" -> "help" or "enable"
- "aforementioned" -> name the thing directly
- "in the event that" -> "if"

#### Automation

```sh
python3 ../cqa-assess/scripts/check-simple-words.py "$DOCS_REPO"
```

Scans prose in `topics/` and `assemblies/` for all 10 complex word patterns. Excludes code blocks, comments, attributes, and table content. Reports each violation with file, line, matched word, replacement, and context. Exits 0 (pass) or 1 (issues found).

### Q4: Readability

#### Flesch-Kincaid Grade Level

The readability score is computed using the Flesch-Kincaid formula:

```text
FK Grade = 0.39 * (words/sentences) + 11.8 * (syllables/words) - 15.59
```

#### Thresholds

| Level | Grade | Meaning |
|-------|-------|---------|
| Ideal | <=10 | 9th-10th grade, accessible to non-native English speakers |
| Minimum | <=12 | 11th-12th grade, Red Hat customer content average |
| Advanced | >12 | Above minimum, review for simplification |

- The overall grade across all files must be <=12 to pass
- Individual files above grade 12 due to technical terminology density (Kubernetes, OpenShift, authentication, configuration) are acceptable
- Files with fewer than 3 sentences are excluded from per-file analysis (volatile FK scores)

#### What affects the grade

- **Average sentence length** — shorter sentences lower the grade (see Q1 scannability)
- **Syllables per word** — simpler words lower the grade (see Q3 simple words)
- **Technical terms** — product names, Kubernetes resources, and infrastructure terms are acceptable complexity. Assess overall flow, not individual jargon-heavy sentences.

#### Automation

```sh
python3 ../cqa-assess/scripts/check-readability.py "$DOCS_REPO"
```

Computes Flesch-Kincaid Grade Level for prose in `topics/` and `assemblies/`. Resolves AsciiDoc attributes to their actual text for accurate syllable counting. Reports overall grade, per-file grades, and grade distribution. Exits 0 (overall <=12) or 1 (overall >12).

#### Scoring

| Score | Criteria |
|-------|----------|
| **4** | Overall FK grade <=10 (ideal range), no complex words (Q3), avg words/sentence <=22 |
| **3** | Overall FK grade 10-12, minor issues in individual files due to jargon density |
| **2** | Overall FK grade >12, multiple files with high grades from genuinely complex prose |
| **1** | Readability not assessed or widespread complexity issues |

### Q5: Fluff

Flag and rewrite:

- "This section describes..."
- "This section provides..."
- "This topic covers..."
- "as mentioned above/below"
- "Learn how to..." / "Learn about..." / "Learn more about..."
- "In this chapter/section/topic..."
- "The following describes..."
- "This procedure/document describes..."
- "It is important to note that..." -> state the fact directly
- "Please note that..." -> remove entirely or state directly

#### Automation

```sh
python3 ../cqa-assess/scripts/check-fluff.py "$DOCS_REPO"
```

Scans prose in `topics/`, `assemblies/`, and `snippets/` for 11 fluff patterns. Excludes code blocks, comments, attributes, and table content. Reports each violation with file, line, matched text, fix guidance, and context. Exits 0 (pass) or 1 (issues found).

#### Scoring

| Score | Criteria |
|-------|----------|
| **4** | 0 fluff patterns found, no self-referential abstracts, no unnecessary introductions |
| **3** | 1-3 minor fluff patterns (borderline cases like "as described in" with xref) |
| **2** | Multiple fluff patterns, self-referential abstracts common |
| **1** | Fluff not assessed or widespread issues |

### Q18: Style guide compliance

- Follows Red Hat supplementary style guide
- Follows IBM Style guide (primary authority)
- See your project's style rules documentation for specific rules

#### IBM Style key rules

**Future tense avoidance:**
- Do not use "will" for actions that happen as a result of user input or system behavior
- Use present tense: "the system creates" not "the system will create"
- Use present tense for consequences: "this causes" not "this will cause"
- Exception: "will" is acceptable for genuine future events or promises ("the feature will be available in the next release")

**Active voice:**
- Prefer active voice over passive voice: "the autoscaler adds a node" not "a node is being added by the autoscaler"
- Identify the actor and make it the subject: "you must set the username" not "the username must be set"
- Passive voice is acceptable when the actor is unknown, irrelevant, or the system itself

**Anthropomorphism:**
- Do not attribute human characteristics to software or hardware
- Incorrect: "the system thinks", "the server wants", "the tool knows", "the plugin tries to understand"
- Correct: "the system processes", "the server requires", "the tool detects", "the plugin parses"
- Exception: Industry-standard terms like "the server listens on port 8080" are acceptable

**Possessives of brand/product names:**
- Never use possessive forms of product or brand names
- Incorrect: "OpenShift's configuration", "Dev Spaces's dashboard", "Kubernetes's API"
- Correct: "the OpenShift configuration", "the Dev Spaces dashboard", "the Kubernetes API"

**Phrasal verbs:**
- Replace informal phrasal verbs with single-word equivalents
- "make sure" → "ensure" or "verify"
- "set up" → "configure" (when referring to configuration)
- "find out" → "determine"
- "carry out" → "perform" or "run"

**Parallelism in lists:**
- All items in a list must use the same grammatical structure
- If the first item starts with a verb, all items must start with a verb
- If the first item is a noun phrase, all items must be noun phrases
- Incorrect: "* Configure the server\n* The client settings\n* Running the tests"
- Correct: "* Configure the server\n* Update the client settings\n* Run the tests"

#### Automation

```sh
python3 ../cqa-assess/scripts/check-simple-words.py "$DOCS_REPO"
```

The simple words script checks for phrasal verbs ("make sure", "set up", "find out", "carry out") alongside complex words. For future tense, passive voice, and anthropomorphism, use grep-based searches or the `cqa-tools:cqa-editorial` skill methodology (contextual LLM analysis required to distinguish valid from invalid uses).

### Q20: Tone and conversational style

#### Conversational level

Red Hat product documentation is enterprise documentation for experienced administrators and developers. Per IBM Style, this typically falls under **"less conversational"** — professional, direct, second-person, no contractions. Determine the appropriate level based on the product's target audience.

| Level | Audience | Example |
|-------|----------|---------|
| Most conversational | Marketing, "try and buy" | "Build your dream app." |
| Fairly conversational | New users, getting started | "In minutes, you can set dates and dive in." |
| **Less conversational** | **Experienced users (typical RH product docs)** | **"Configure OAuth to allow users to interact with Git repositories."** |
| Least conversational | API docs, expert audience | "The SObject rows resource retrieves field values." |

#### Tone rules

- Professional, 2nd person ("you") for procedures
- No first person in body text ("I", "we", "our", "us")
- No contractions ("can't" → "cannot", "isn't" → "is not") — contractions are only acceptable in "fairly conversational" cloud services content
- No informal language: "basically", "just", "simply", "pretty", "cool", "stuff", "kind of", "sort of"
- No anthropomorphism — do not attribute human qualities to software (see Q18 IBM Style rules)
- No future tense "will" for immediate consequences — use present tense (see Q18 IBM Style rules)
- No possessive forms of product/brand names (see Q18 IBM Style rules)

#### Common mistakes to avoid (IBM Style)

- Making everything a question or exclamation
- Overusing sentence fragments for effect
- Overusing punctuation for effect
- Attempting humor that is not universal or timeless
- Forgetting content must be appropriate for a global audience and translation

#### Homographs

Be aware of words spelled the same but with different meanings. Avoid using homographs close together in a sentence. Common homographs in technical docs: application, attribute, block, coordinates, number, object, project.

#### What to check

1. Search for contractions in prose (not code blocks or comments)
2. Search for first person pronouns ("we ", "our ", "us ", "I ")
3. Search for informal words: "just", "simply", "basically", "pretty", "cool", "stuff", "kind of", "sort of", "a lot", "lots of"
4. Search for exclamation marks in prose (not code blocks)
5. Search for rhetorical questions in headings or body text
6. Verify consistent second-person ("you") usage in procedures

#### Scoring

| Score | Criteria |
|-------|----------|
| **4** | 0 contractions, 0 first person, 0 informal words in prose, consistent 2nd person, no exclamations/questions for effect, appropriate for global audience |
| **3** | 1-3 informal words or minor tone inconsistencies |
| **2** | Multiple contractions, first person usage, or informal language patterns |
| **1** | Tone not assessed or widespread informality |

## Scoring

See [scoring-guide.md](../../reference/scoring-guide.md).
