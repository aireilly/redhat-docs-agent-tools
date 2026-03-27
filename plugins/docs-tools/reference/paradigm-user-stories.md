# User stories (feature-based) content paradigm

This reference defines the feature-based / user-story content paradigm for documentation planning and writing. Read the section relevant to your role.

## For planners

### Feature-based information architecture

Structure documentation around product capabilities, features, and components — reflecting how the product is built and how users interact with it. Use user stories to scope individual documentation modules.

### Why feature-based organization works

- **Matches the product mental model**: Users often approach documentation by feature name or component — organizing around these terms aligns with how they search and navigate.
- **Scales with the product**: As features are added, new sections are added naturally without restructuring the entire documentation hierarchy.
- **Direct mapping to engineering**: Features and components map directly to engineering teams, code modules, and release notes — making collaboration and maintenance straightforward.
- **Clear ownership boundaries**: Each feature section has a clear scope, reducing ambiguity about where new content belongs.

### Core principles

1. **Organize by features and components**: Structure documentation around product capabilities, features, and components rather than abstract user goals.

2. **Follow the feature-based hierarchy**: Implement a three-level structure:
   - **Area** → **Feature (Parent Topic)** → **Task (Specific Procedure or Concept)**

3. **Use user stories for scoping**: Before planning any content, identify the user story:
   - "As a [role], I want [goal] so that [benefit]"
   - User stories determine which modules to create and what content to include

4. **Dynamic categories**: Derive categories from the product's domain and feature landscape. Common patterns include:
   - Component-based: "Authentication", "Networking", "Storage", "Monitoring"
   - Lifecycle-based: "Installation", "Configuration", "Administration", "Troubleshooting"
   - Audience-based: "Developer Guide", "Operator Guide", "API Reference"

   Choose the categorization scheme that best fits the product and its users. Do not use a fixed category list — adapt to the product domain.

5. **Use descriptive, feature-focused titles**:
   - **Good**: "Configuring horizontal pod autoscaling" (clear feature reference)
   - **Bad**: "Scale applications based on demand" (too abstract)

6. **Apply active phrasing for procedures**: Use imperatives and name the feature (e.g., "Configure RBAC policies", "Install the monitoring agent").

7. **Use industry-standard terminology**: Industry-standard terms (SSL, HTTP, OAuth, API, RBAC, CI/CD) are acceptable. Avoid product-specific internal vocabulary.

8. **Feature-scoped parent topics**: Each major feature or component gets a parent topic that introduces the feature, explains its purpose, and links to tasks within it.

9. **User stories for child modules**: Each feature's child modules correspond to specific user stories that exercise that feature.

### Module planning with user stories

For each documentation need, identify the user story and map it to the feature hierarchy:

**Step 1: Define the user story** (internal planning only)
- "As a [role], I want [goal] so that [benefit]"
- Example: "As a cluster administrator, I want to configure horizontal pod autoscaling so that my applications handle variable traffic without manual intervention."

**Step 1b: Check for existing feature topics before creating new parent topics**
- Before creating a new parent topic, check whether the feature is already covered by an existing parent topic in the documentation.
- New capabilities within an existing feature should be added as child modules under the existing parent topic — not as new parent topics.
- Only create a new parent topic when the feature is genuinely new and distinct from all existing documented features.

**Step 2: Map to the feature hierarchy**
- **Area**: Broad domain derived from the product (e.g., "Networking", "Security", "Storage")
- **Feature / Parent Topic**: The specific capability (e.g., "Horizontal Pod Autoscaler")
- **Tasks / Child Modules**: Specific procedures, concepts, and references for the feature (e.g., "Configuring HPA thresholds", "HPA architecture", "HPA parameters")

TOC nesting rules:
- Headings in TOCs must not exceed **3 levels** of nesting.
- **Areas do not count** toward nesting depth because they contain no content — they are organizational groupings only.
- Example: `Networking (area) → Ingress Controller (Feature, level 1) → Configuring route timeouts (task, level 2) → Route timeout parameters (reference, level 3)`

**Step 3: Plan Parent Topics**

Every major feature must have a Parent Topic that introduces the feature to users. Parent Topic descriptions serve both human readers and AI/search engines.

Parent Topics must include:
- A clear, descriptive title naming the feature or component
- A description of what the feature does and when to use it
- An overview of the feature's architecture or key components
- An overview of common tasks and their sequence, with links to related content

Example Parent Topic outline:
```
Title: Horizontal pod autoscaler
Description: [What] Automatically adjusts the number of pod replicas based on CPU, memory, or custom metrics. [When] Use when workloads have variable resource demands.
Overview: The HPA controller monitors metrics and adjusts replica counts within configured bounds.
Common tasks: 1. Configure HPA for a deployment → 2. Set custom metrics → 3. Monitor scaling events
```

### Plan template: paradigm-specific sections

When populating the documentation plan template, use these feature-based sections:

**Section 1** (replaces the generic "JTBD" section):

```markdown
## What are the primary user stories?

[List the key user stories in "As a [role], I want [goal] so that [benefit]" format, derived from your research]
```

**Section 2** (replaces the generic "JTBD workflow" section):

```markdown
## How do these features relate to the user's workflow?

[Explain how the documented features fit into the user's broader end-to-end workflow]
```

**Support status section header**: Use "What is the support status of the feature(s)?"

**JIRA ticket description** — post only these sections:
1. `## What are the primary user stories?`
2. `## How do these features relate to the user's workflow?`
3. `## Who can provide information and answer questions?`
4. `## New Docs`
5. `## Updated Docs`

### Key principles (feature-based specific)

1. **Feature-based organization**: Plan documentation around product features and components, organized by how users interact with them
2. **Descriptive titles**: Use clear, feature-descriptive titles that name the capability or component
3. **Parent Topics first**: Every major feature needs a Parent Topic that introduces the capability and links to tasks

---

## For writers

### Titling strategy

Use clear, descriptive titles that name the feature or component:

| Type | Bad (Too abstract) | Good (Feature-descriptive) |
|------|-------------------|---------------------------|
| CONCEPT | "How autoscaling responds to demand" | "Horizontal pod autoscaler architecture" |
| PROCEDURE | "Scale applications automatically" | "Configuring horizontal pod autoscaling" |
| REFERENCE | "Autoscaling configuration options" | "HPA configuration parameters" |
| ASSEMBLY | "Scale applications based on demand" | "Horizontal pod autoscaler" |

### Writing with feature focus

- **Abstracts**: Describe what the feature does and when to use it
- **Procedures**: Frame steps around configuring or using the specific feature
- **Concepts**: Explain the feature's architecture, components, and design decisions
- **References**: Present parameters, options, and specifications for the feature

### Title and heading conventions

- **Length**: 3-11 words, sentence case, no end punctuation
- **Feature-descriptive**: Name the feature or component clearly
- **Concept titles**: Noun phrase naming the feature (e.g., "Horizontal pod autoscaler architecture")
- **Procedure titles**: Imperative verb phrase naming the feature (e.g., "Configuring horizontal pod autoscaling")
- **Reference titles**: Noun phrase for the data set (e.g., "HPA configuration parameters")
- **Assembly titles** (AsciiDoc only): Feature name (e.g., "Horizontal pod autoscaler")
- Industry-standard terms (SSL, API, RBAC) are acceptable; avoid product-specific vocabulary
