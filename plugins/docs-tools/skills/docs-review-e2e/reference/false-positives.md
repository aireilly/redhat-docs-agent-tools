# False Positives

When evaluating issues during review, do NOT flag the following — they are false positives:

- Pre-existing issues in unchanged content
- Something that appears to be a style violation but is an accepted project convention
- Pedantic nitpicks that a senior technical writer would not flag
- Issues that Vale will catch automatically (do not run Vale to verify unless the agent has Vale available)
- General quality concerns (e.g., "could be more concise") unless they violate a specific rule
- Style suggestions that conflict with existing content in the same document
- Terminology that matches the product's official naming even if it differs from the style guide
- Minor stylistic preferences that don't affect clarity
- Potential issues that depend on context outside the changed files
- Subjective wording suggestions unless they violate a specific style rule
