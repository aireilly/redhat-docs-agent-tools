# Example JTBD TOC

This example demonstrates the correct format for a JTBD-oriented Table of Contents. Use this as a reference for structure, formatting, and style.

---

## Example: Creating a Workbench

```markdown
# Creating a Workbench
**Jobs-To-Be-Done Oriented Table of Contents**

*Organized by user goals and workflow stages*

---

## Guide Overview

**Purpose:** Enable platform engineers to create custom workbench images and provision development environments programmatically using Kubernetes CRDs.

**Personas:** Paula the Platform Engineer

**Main Jobs:** 3 core jobs across 2 workflow stages (Plan, Configure)

---

## Quick Navigation

**I want to:**
- Understand my options for creating workbenches -> Job 1 (Plan)
- Create a custom notebook image -> Job 2 (Configure)
- Provision a workbench programmatically -> Job 3 (Configure)
- Configure OAuth authentication -> Job 3.2 (Configure)
- Set up resource limits for workbenches -> Job 3.3 (Configure)
- Verify my workbench was created correctly -> Job 3.5 (Configure)

---

# Table of Contents

## Choose Your Approach

### Job 1: Understand Workbench Creation Options
*When I need to provide data scientists with customized development environments*

**Personas:** Paula the Platform Engineer

#### Evaluate Available Methods

**Context:** Three distinct approaches exist for creating workbenches and custom images, each suited to different skill levels and use cases.

- **Decision:** Choose creation method based on requirements

| Method | Best For | Skills Required |
|--------|----------|-----------------|
| CRD/CLI (this guide) | Automation, GitOps, consistency | Kubernetes, YAML, CLI |
| OpenShift APIs | Programmatic integration | API development |
| Dashboard UI | Quick setup, any user | Basic UI navigation |

-> Lines 22-35 (Chapter 1: Overview): Overview of workbench creation options

---

## Set Up & Configure

### Job 2: Create a Custom Workbench Image
*When I need to make a custom container image available to data scientists in the OpenShift AI dashboard*

**Personas:** Paula the Platform Engineer

**Requires:**
- Cluster administrator privileges for OpenShift cluster
- OpenShift CLI (oc) installed

#### 2.1 Define ImageStream Configuration
**Goal:** Author the ImageStream CRD manifest with proper metadata and dashboard visibility settings.

- **Task:** Create ImageStream YAML manifest
  -> Lines 36-70 (Chapter 2: Creating a custom image): ImageStream CRD structure

- **Task:** Configure dashboard visibility labels
  -> Lines 70-100 (Chapter 2: Creating a custom image): Required labels

  **Required Labels:**
  - `opendatahub.io/dashboard: 'true'` - Makes image visible in dashboard
  - `opendatahub.io/notebook-image: 'true'` - Identifies as notebook image

#### 2.2 Apply and Verify ImageStream (Confirmation Step)
**Goal:** Confirm the ImageStream was created and obtain the image URL.

- **Task:** Apply the ImageStream CRD
  ```bash
  oc apply -f imagestream.yaml
  ```

- **Task:** Verify ImageStream creation
  -> Lines 200-280 (Chapter 2: Creating a custom image): Verification procedure
  ```bash
  oc describe imagestream <imagestream-name> -n redhat-ods-applications
  ```

- **Validation:** Image appears in OpenShift AI dashboard workbench image dropdown

---

### Job 3: Provision Workbench Environment
*When I need to create a development environment programmatically for automation and consistency*

**Personas:** Paula the Platform Engineer

**Requires:**
- Cluster administrator privileges
- OpenShift CLI (oc) installed
- Project/namespace created
- Container image URL (from Job 2 or existing image)

#### 3.1 Define Core Workbench Profile (The "Standard" Setup)
**Goal:** Author the Notebook CRD manifest with essential configuration.

- **Task:** Define workbench metadata (name, namespace, labels)
  -> Lines 370-420 (Chapter 3: Creating a workbench): Notebook CRD metadata section

- **Task:** Specify notebook container image
  -> Lines 820-900 (Chapter 3: Creating a workbench): Image configuration

- **Task:** Set resource limits and requests
  -> Lines 600-700 (Chapter 3: Creating a workbench): CPU, memory, GPU allocation

#### 3.2 Implement Security Hardening (The "Secure" Setup)
**Goal:** Secure access and communications for the workbench.

- **Task:** Configure OAuth Authentication
  -> Lines 365-370 (Chapter 3.2: OAuth configuration): inject-oauth annotation

  **Annotation:**
  ```yaml
  kubeflow-resource-stopped: inject-oauth
  ```

- **Task:** Configure SSL/TLS Certificates
  -> Lines 440-500 (Chapter 3.3: SSL configuration): Environment variables

  **Environment Variables:**
  - `PIP_CERT` - Certificate for pip
  - `GIT_SSL_CAINFO` - Certificate for git

#### 3.3 Configure Workflow Integrations (The "Integrated" Setup)
**Goal:** Connect workbench to data sources and scheduling systems.

- **Task:** Attach Data Connections
  -> Lines 1000-1100 (Chapter 3.4: Data connections): Secret references

- **Task:** Enable Kueue Integration
  -> Lines 900-1000 (Chapter 3.5: Kueue): Queue label configuration

#### 3.4 Apply and Verify Workbench (Confirmation Step)
**Goal:** Confirm the workbench was provisioned successfully.

- **Task:** Apply the Notebook CRD
  ```bash
  oc apply -f notebook.yaml
  ```

- **Task:** Verify workbench status
  ```bash
  oc describe notebook <workbench-name> -n <project>
  ```

- **Validation:** Workbench shows "Running" status, OAuth proxy sidecar present

---

## Appendices

### A. CRD Quick Reference

| CRD | Purpose | Required |
|-----|---------|----------|
| ImageStream | Custom notebook images | For custom images |
| Notebook | Workbench definition | Always |
| Secret | Data connections | For data access |

### B. Common Troubleshooting

| Issue | Solution |
|-------|----------|
| Image not visible in dashboard | Check `opendatahub.io/dashboard: 'true'` label |
| Workbench not starting | Verify resource quota availability |
| OAuth proxy not injecting | Check annotation spelling |

---

## Navigation Guide

### By User Journey

**Platform Engineer setting up custom environment:**
1. Job 1: Understand available creation methods
2. Job 2: Create and register custom image
3. Job 3: Provision workbench using custom image

**Platform Engineer automating existing setup:**
1. Job 3: Provision workbench with existing image
   - Skip to Job 3.1 if using default images

---

## Document Statistics

**Workflow Coverage:**
- Plan: 1 job
- Configure: 2 jobs

**Main Jobs:** 3
**User Stories/Paths:** 8 themed sections
**Source Sections:** 15 referenced

---
```

## Key Elements Demonstrated

### 1. Title & Overview
- Clear purpose statement
- Personas listed
- Job count summary

### 2. Quick Navigation
- "I want to..." format
- Links to specific jobs
- Stage context in parentheses

### 3. Job Numbering
- Sequential (1, 2, 3...)
- Sub-sections use X.Y format (3.1, 3.2...)

### 4. Job Entries
- Clean title: [Verb] + [Object]
- *When* context in italics
- **Personas:** who does this
- **Requires:** only when non-obvious

### 5. Themed Sections
- "Standard" / "Secure" / "Integrated" setup labels
- **Goal:** statement for each section
- **Task:** prefix for individual items

### 6. Line References
- Include section name: `Lines X-Y (Chapter Name): Description`
- Source context for navigation

### 7. Confirmation Steps
- Final section within execution jobs
- **Validation:** expected outcome

### 8. Tables for Decisions
- Comparison matrices where helpful
- Quick reference tables in appendices
