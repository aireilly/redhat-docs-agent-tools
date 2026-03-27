# JTBD (Jobs to Be Done) content paradigm

This reference defines the Jobs to Be Done content paradigm for documentation planning and writing. Read the section relevant to your role.

## For planners

### JTBD framework

Apply a Jobs to Be Done mindset to all documentation planning. This means shifting from "what the product does" (feature-focused) to "what the user is trying to accomplish" (outcome-focused). Prioritize the user's underlying motivation — the reason they "hire" the product — over technical specifications.

### Why JTBD matters for documentation planning

- **Reduces topic proliferation**: Unless a new feature corresponds to a genuinely new user job, new enhancements are updates to existing job-based topics — not new parent topics.
- **Addresses emotional and social dimensions**: Jobs have functional, emotional, and social aspects. Users want peace of mind, to feel secure, and to look competent to their peers. Documentation that acknowledges these dimensions (e.g., "reliably," "with confidence," "without risking data loss") resonates more strongly than purely functional descriptions.
- **Improves AI and search discoverability**: As documentation is ingested by AI and search engines, outcome-focused content surfaces solutions for users trying to resolve their business problems — not just product names.
- **Reduces support queries**: Intuitive, job-aligned documentation reduces mental effort and frustration, leading to fewer support tickets.
- **Creates timeless structure**: Jobs do not change over time. While the technology used to accomplish them evolves, the fundamental user need remains the same — making JTBD-organized documentation inherently stable.

### Core principles

1. **Organize by outcomes, not features**: Structure documentation around user goals ("Top Jobs") rather than internal product modules or feature names.

2. **Follow the JTBD hierarchy**: Implement a three-level structure:
   - **Category** → **Top Job (Parent Topic)** → **User Story (Specific Task)**

3. **Frame the user's job**: Before planning any content, identify the job statement:
   - "When [situation], I want to [motivation], so I can [expected outcome]"
   - This job statement informs planning decisions but does NOT appear in final documentation

4. **Distinguish JTBD from User Stories**: JTBD and user stories are complementary but distinct:

   | Dimension | JTBD | User Story |
   |-----------|------|------------|
   | Format | "When [situation], I want to [motivation], so I can [outcome]" | "As a [user], I want [goal] so that [benefit]" |
   | Focus | **What** the user wants to achieve + **Why** it matters | **How** the user will use a specific feature |
   | Scope | High-level, broad — overarching user goals | Detailed, specific — single actionable task |
   | Maps to | Top Jobs (Parent Topics) | Level 3 tasks (child modules) |

   A single JTBD contains multiple user stories. Use JTBD to define navigation and parent topics; use user stories to plan the child modules within each parent topic.

5. **Use natural language**: Avoid product-specific buzzwords or internal vocabulary. Use terms users naturally use when searching for solutions.

6. **Draft outcome-driven titles**:
   - **Bad**: "Ansible Playbook Syntax" (feature-focused)
   - **Good**: "Define automation workflows" (outcome-focused)

7. **Apply active phrasing**: Use imperatives and task-oriented verbs (e.g., "Set up," "Create," "Control") and state the context or benefit when helpful.

8. **Use industry-standard terminology when appropriate**: Industry-standard terms (SSL, HTTP, OAuth, API, RBAC, CI/CD) are acceptable in titles and content. Avoid *product-specific* vocabulary (e.g., internal feature names), but do not avoid universally understood technical terms.

9. **State the benefit or context in titles**: When two titles could sound similar, add context to differentiate:
   - **Bad**: "Managing Roles and Permissions"
   - **Good**: "Control team access with roles and permissions"

   Technique: reverse-engineer titles from job statements. Write the user story ("As a [user], I want to [goal], so that I can [benefit]"), then extract a title from the goal and benefit.
   - User story: "As a project manager, I want to export task reports so I can review team progress."
   - Title: "Review team progress by exporting task reports"

10. **Use only approved JTBD categories**: Structure documentation according to the following defined Categories. Do not create new categories.
    - What's new
    - Discover
    - Get started
    - Plan
    - Install
    - Upgrade
    - Migrate
    - Administer
    - Develop
    - Configure
    - Secure
    - Observe
    - Integrate
    - Optimize
    - Extend
    - Troubleshoot
    - Reference

### Module planning with JTBD

For each documentation need, first identify the user's job:

**Step 1: Define the job statement** (internal planning only)
- "When [situation], I want to [motivation], so I can [expected outcome]"
- Example: "When I have a new application ready for deployment, I want to configure the runtime environment, so I can run my application reliably in production."

**Step 1b: Check for existing jobs before creating new parent topics**
- Before creating a new parent topic, check whether the user's goal is already covered by an existing job in the documentation.
- Unless a new feature corresponds to a genuinely new user job, it should be an update to an existing job-based topic — not a new parent topic.
- Only create a new parent topic when the user's goal is fundamentally distinct from all existing jobs.
- This prevents topic proliferation and keeps the documentation structure stable over time.

**Step 2: Map to the JTBD hierarchy**
- **Category**: Broad area, must be selected from the defined list
- **Top Job / Parent Topic**: The user's main goal (e.g., "Deploy applications to production")
- **User Stories / Tasks**: Specific steps to achieve the goal (e.g., "Configure the runtime," "Set up monitoring")

TOC nesting rules:
- Headings in TOCs must not exceed **3 levels** of nesting.
- **Categories do not count** toward nesting depth because they contain no content — they are organizational groupings only.
- Example: `Configure (category) → Control access to resources (Top Job, level 1) → Set up RBAC (user story, level 2) → RBAC configuration options (reference, level 3)`

**Step 3: Plan Parent Topics**

Every major job must have a Parent Topic that serves as the starting point for users looking to achieve the desired outcome. Parent Topic descriptions serve both human readers and AI/search engines — including "the what" and "the why" helps both audiences find the right content.

Parent Topics must include:
- A product-agnostic title using natural language (this becomes the TOC entry for the job)
- A description of "the what" (the desired outcome) and "the why" (the motivation/benefit)
- A high-level overview of how the product helps users achieve this specific goal
- An overview of the high-level steps to achieve the goal, with links to related content

Example Parent Topic outline:
```text
Title: Improve application performance
Description: [What] Tune the platform for demanding workloads. [Why] Keep applications responsive and resource usage efficient.
Overview: The product provides tools for resource allocation, pod scheduling, and workload profiling.
High-level steps: 1. Profile workloads → 2. Configure resource limits → 3. Monitor results
```

### Content journey mapping note

JTBD provides the **why** — the user's underlying motivation and desired outcome. Content journeys provide the **how** and **where** — the specific steps a user takes and where content can best assist them. Always define the JTBD first, then use content journeys to identify lifecycle gaps.

### Plan template: paradigm-specific sections

When populating the documentation plan template, use these JTBD-specific sections:

**Section 1** (replaces the generic "user stories" section):

```markdown
## What is the main JTBD? What user goal is being accomplished? What pain point is being avoided?

[Write the completed job statement using your research findings]
When [actual circumstance], I want to [actual motivation], so that I can [actual goal] while avoiding [actual pain point].
```

**Section 2** (replaces the generic "workflow" section):

```markdown
## How does the JTBD(s) relate to the overall real-world workflow for the user?

[Explain how the JTBD fits into the user's broader end-to-end workflow]
```

**Support status section header**: Use "What is the support status of the feature(s) being used to complete the user's JTBD (Job To Be Done)?"

**JIRA ticket description** — post only these sections:
1. `## What is the main JTBD? What user goal is being accomplished? What pain point is being avoided?`
2. `## How does the JTBD(s) relate to the overall real-world workflow for the user?`
3. `## Who can provide information and answer questions?`
4. `## New Docs`
5. `## Updated Docs`

### Key principles (JTBD-specific)

1. **Jobs to Be Done**: Plan documentation around what users are trying to accomplish, not what the product does
2. **Outcome-focused titles**: Use natural language that describes user goals, not feature names
3. **Topic proliferation control**: Do not create new parent topics for features that fit within an existing job — only create new parent topics for genuinely new user goals
4. **JTBD before content journeys**: Define the user's job (the why) before mapping content journeys (the how/where)

---

## For writers

### Titling strategy

Use outcome-driven titles with natural language:

| Type | Bad (Feature-focused) | Good (Outcome-focused) |
|------|----------------------|------------------------|
| CONCEPT | "Autoscaling architecture" | "How autoscaling responds to demand" |
| PROCEDURE | "Configuring HPA settings" | "Scale applications automatically" |
| REFERENCE | "HPA configuration parameters" | "Autoscaling configuration options" |
| ASSEMBLY | "Horizontal Pod Autoscaler" | "Scale applications based on demand" |

### Writing with JTBD

- **Abstracts**: Describe what the user will achieve, not what the product does
- **Procedures**: Frame steps around completing the user's job
- **Concepts**: Explain how understanding this helps the user succeed
- **References**: Present information users need to complete their job

### Title and heading conventions

- **Length**: 3-11 words, sentence case, no end punctuation
- **Outcome-focused**: Describe what users achieve, not product features
- **Concept titles**: Noun phrase (e.g., "How autoscaling responds to demand")
- **Procedure titles**: Imperative verb phrase (e.g., "Scale applications automatically")
- **Reference titles**: Noun phrase (e.g., "Autoscaling configuration options")
- **Assembly titles** (AsciiDoc only): Top-level user job (e.g., "Manage application scaling")
- Industry-standard terms (SSL, API, RBAC) are acceptable; avoid product-specific vocabulary
