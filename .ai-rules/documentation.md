# Documentation Rules

## Purpose

Create and maintain professional, accurate, easy-to-navigate project documentation inspired by the presentation quality and usability patterns used in repositories from:

`https://github.com/jaktestowac`

Use that source only as a quality and structure reference. Do not copy its wording, branding, images, or project-specific content.

The documentation must help a new developer or reviewer quickly understand:

- what the project does,

- why it exists,

- how it is structured,

- how to run it,

- how to test it,

- how to configure and deploy it,

- what is production-ready,

- what limitations or risks remain.

Documentation is part of the product. Treat incorrect documentation as a defect.

---

## Core principles

1. **Accuracy over appearance**

   - Never document behavior that was not verified in the repository.

   - Never invent commands, environment variables, endpoints, workflows, features, badges, deployment targets, test counts, coverage values, or production-readiness claims.

   - Verify facts against source code, configuration, tests, CI workflows, deployment files, and current application behavior.

2. **Useful before exhaustive**

   - Optimize for a reader who sees the repository for the first time.

   - Put the most important information first.

   - Keep the root `README.md` focused on orientation and onboarding.

   - Move detailed operational or architectural material into dedicated files under `docs/`.

3. **One source of truth**

   - Do not duplicate the same detailed instructions across multiple files.

   - Keep one canonical document for each subject.

   - Other documents should link to the canonical source instead of repeating it.

4. **Current repository state**

   - Documentation must describe the code that currently exists, not abandoned plans or historical assumptions.

   - Clearly separate:

     - implemented behavior,

     - partially implemented behavior,

     - planned work,

     - known limitations.

5. **Reader-oriented structure**

   - Use descriptive headings, short paragraphs, tables, lists, diagrams, and copy-ready commands.

   - Make documentation easy to scan.

   - Avoid walls of text and unnecessary theory.

6. **Professional but restrained presentation**

   - Use badges, icons, callouts, screenshots, and diagrams only when they improve comprehension.

   - Do not turn documentation into decorative marketing material.

   - Do not overload headings with emojis.

---

## Required repository audit before editing documentation

Before creating or updating documentation, inspect the repository and establish the actual state of the project.

At minimum, inspect relevant files from the following categories:

- root directory structure,

- application entry points,

- dependency manifests,

- lock files,

- configuration modules,

- `.env.example` files,

- Dockerfiles and Compose files,

- database models and migrations,

- API routes or controllers,

- frontend routes and key user flows,

- test configuration and test directories,

- CI/CD workflows,

- deployment configuration,

- observability configuration,

- security-related configuration,

- existing Markdown files,

- roadmap, backlog, ADR, and technical-debt files.

Do not rely only on the existing `README.md`. Existing documentation may be outdated.

### Documentation inventory

Create an internal inventory of all documentation files and classify each one as:

- **KEEP** — accurate and useful,

- **UPDATE** — useful but outdated or incomplete,

- **MERGE** — duplicates another document,

- **ARCHIVE** — historically useful but no longer current,

- **DELETE** — obsolete, misleading, empty, or redundant.

Prefer removing obsolete documentation over preserving misleading files.

Do not delete historical ADRs merely because the implementation changed. Supersede them explicitly when appropriate.

---

## Documentation architecture

Use the following structure only where it is relevant to the project:

```text

[README.md](http://README.md)

docs/

├── [README.md](http://README.md)

├── [ARCHITECTURE.md](http://ARCHITECTURE.md)

├── [API.md](http://API.md)

├── [TESTING.md](http://TESTING.md)

├── [DEPLOYMENT.md](http://DEPLOYMENT.md)

├── [CONFIGURATION.md](http://CONFIGURATION.md)

├── [SECURITY.md](http://SECURITY.md)

├── [OPERATIONS.md](http://OPERATIONS.md)

├── [TROUBLESHOOTING.md](http://TROUBLESHOOTING.md)

├── [ROADMAP.md](http://ROADMAP.md)

├── TECH_[DEBT.md](http://DEBT.md)

└── adr/

    ├── [README.md](http://README.md)

    └── [0001-example-decision.md](http://0001-example-decision.md)

```

Do not create empty placeholder documents.

Create a dedicated file only when the subject is large enough to justify it.

### Root `README.md`

The root README is the project's landing page. It should let a reader understand and start the project without reading the entire documentation set.

### `docs/README.md`

When the project contains several documentation files, create or maintain `docs/README.md` as a documentation index.

Group links by purpose, for example:

- Getting started

- Architecture

- Development

- Testing

- Deployment and operations

- Security

- Decisions

- Planning

Each link should include a one-sentence description.

---

## Required README structure

Use the following order as a default. Remove sections that genuinely do not apply and add project-specific sections when needed.

### 1. Project title and value proposition

Start with:

- project name,

- concise one-sentence purpose,

- target user or use case,

- current lifecycle status when relevant.

A new reader should understand the project within the first few lines.

Avoid vague descriptions such as:

- “modern application,”

- “production-ready solution,”

- “powerful platform,”

- “scalable system,”

unless the repository contains evidence supporting those claims.

### 2. Status and badges

Use a small, relevant badge group when verified, for example:

- CI status,

- test status,

- coverage,

- supported runtime version,

- license,

- deployment status,

- code quality.

Badge rules:

- Every badge must resolve correctly.

- Workflow badges must reference real workflow files and the correct branch.

- Do not display hard-coded test counts or coverage percentages that will quickly become stale.

- Do not use badges that communicate no useful project information.

- Prefer no badge over a broken or misleading badge.

- Keep the badge row visually restrained.

### 3. Visual overview

When useful and available, add one of:

- product screenshot,

- short demo GIF,

- architecture diagram,

- request-flow diagram.

Rules:

- Use repository-owned assets.

- Store documentation assets in a consistent location such as `docs/assets/`.

- Add meaningful alt text.

- Do not add screenshots that expose credentials, personal data, internal URLs, tokens, or customer information.

- Do not create decorative images unrelated to project understanding.

### 4. Project overview

Explain briefly:

- the problem,

- the solution,

- the main workflow,

- the repository's scope,

- important boundaries or non-goals.

Prefer concrete domain language over generic software terminology.

### 5. Table of contents

For a medium or large README, include a manually maintained table of contents with relative anchor links.

The table of contents must match the actual heading structure.

Do not include a table of contents in a very short README where it adds no value.

### 6. Key features

Describe implemented capabilities in grouped, reader-friendly categories.

Good categories may include:

- Core product flows

- Authentication and authorization

- API

- Background processing

- Integrations

- Data and persistence

- Testing and quality

- Security

- Observability

- Deployment

Do not list dependencies as product features.

Mark incomplete capabilities explicitly.

### 7. Architecture

Provide a concise architecture overview covering the components that actually exist.

Depending on the project, include:

- frontend,

- backend,

- database,

- cache,

- queue or worker,

- external integrations,

- object storage,

- CI/CD,

- observability.

Use a Mermaid diagram only when it makes the flow easier to understand.

Diagram rules:

- Match real component names.

- Show meaningful relationships.

- Avoid speculative services.

- Avoid large decorative diagrams that cannot be maintained.

- Keep detailed architectural reasoning in `docs/ARCHITECTURE.md` or ADRs.

### 8. Technology stack

Use a compact table:

| Area | Technology | Purpose |

|---|---|---|

| Backend | FastAPI | HTTP API and application services |

| Database | PostgreSQL | Persistent relational storage |

| Tests | pytest | Automated backend tests |

Only list technologies used by the current repository.

Do not create an oversized “skills cloud” or list every transitive dependency.

### 9. Getting started

The quick-start path must be copy-ready and ordered.

Include, where relevant:

1. prerequisites,

2. cloning,

3. environment setup,

4. dependency installation,

5. service startup,

6. database migration,

7. seed or demo data,

8. application URLs,

9. verification command.

Every command must be valid from the stated working directory.

Example format:

```bash

git clone <repository-url>

cd <repository-directory>

cp .env.example .env

docker compose up --build

```

After commands, state the expected result, for example:

- frontend URL,

- API URL,

- OpenAPI URL,

- health endpoint,

- default demo flow.

Do not include real secrets or credentials.

### 10. Configuration

Document:

- required environment variables,

- optional environment variables,

- defaults,

- accepted formats,

- where each value is used,

- security implications when relevant.

Prefer a table:

| Variable | Required | Default | Description |

|---|---:|---|---|

| `DATABASE_URL` | Yes | — | PostgreSQL connection string |

| `LOG_LEVEL` | No | `INFO` | Application log level |

Use `.env.example` as the canonical machine-readable configuration template.

The README or configuration guide must stay consistent with `.env.example` and configuration code.

### 11. Development workflow

Document the real developer workflow, including relevant commands for:

- starting development services,

- formatting,

- linting,

- type checking,

- migrations,

- tests,

- local CI-equivalent validation.

Use the commands already supported by the repository.

Do not introduce undocumented wrapper commands merely to make the README look cleaner.

### 12. Testing and quality

Explain:

- test layers that exist,

- what each layer protects,

- how to run targeted tests,

- how to run the full suite,

- coverage policy when enforced,

- CI quality gates,

- notable test limitations.

Example:

| Layer | Tool | Scope |

|---|---|---|

| Unit | pytest | Domain and service logic |

| Integration | pytest + PostgreSQL | Persistence and API contracts |

| Frontend | Vitest | Components and client logic |

Do not claim that tests cover a behavior unless the test suite verifies it.

Keep detailed testing strategy in `docs/TESTING.md`.

### 13. Deployment and operations

Document only real deployment paths.

Include, where relevant:

- target platform,

- build process,

- migration process,

- required secrets,

- health and readiness checks,

- rollback approach,

- smoke tests,

- observability,

- backup and restore.

Do not expose secret values.

Do not describe automatic deployment unless CI/CD actually performs it.

Keep detailed procedures in `docs/DEPLOYMENT.md` or `docs/OPERATIONS.md`.

### 14. Documentation index

Link to detailed documentation with one-sentence descriptions.

Example:

| Document | Purpose |

|---|---|

| `docs/ARCHITECTURE.md`](docs/[ARCHITECTURE.md](http://ARCHITECTURE.md)) | Components, boundaries, and request flows |

| `docs/TESTING.md`](docs/[TESTING.md](http://TESTING.md)) | Test strategy and commands |

| `docs/DEPLOYMENT.md`](docs/[DEPLOYMENT.md](http://DEPLOYMENT.md)) | Deployment and rollback procedures |

Do not link to files that do not exist.

### 15. Project status, limitations, and roadmap

When relevant, state clearly:

- current maturity,

- supported use cases,

- unsupported use cases,

- known technical limitations,

- production-readiness gaps,

- near-term roadmap.

Do not hide important limitations behind marketing language.

Do not mix implemented features with planned features.

If a separate roadmap exists, keep only a concise status summary in the README and link to the roadmap.

### 16. Contributing, security, license, and contact

Include only relevant sections:

- contribution workflow,

- issue reporting,

- security disclosure process,

- license,

- maintainer or support contact.

Link to `CONTRIBUTING.md`, `SECURITY.md`, or `LICENSE` when those files exist.

---

## Style guide

### Language

- Use the repository's established primary documentation language.

- Do not mix Polish and English in the same document without a clear reason.

- When bilingual documentation is intentionally maintained, use clearly named files such as:

  - `README.md` and `README.pl.md`, or

  - `README.md` and `README.eng.md`.

- Keep language versions structurally equivalent.

- Do not create a second language version unless requested or already established.

### Tone

Write in a:

- direct,

- professional,

- concrete,

- technically precise,

- reader-friendly

style.

Avoid:

- exaggerated marketing language,

- AI-generated filler,

- repeated conclusions,

- unnecessary background theory,

- vague claims,

- informal jokes in operational instructions.

### Headings

- Use one `#` heading per document.

- Maintain logical heading hierarchy.

- Do not skip heading levels without a reason.

- Use descriptive headings that make sense outside the local paragraph.

- Keep heading naming consistent across related documents.

### Paragraphs and lists

- Keep paragraphs short.

- Use lists for steps, requirements, options, and grouped facts.

- Use numbered lists when order matters.

- Use tables for structured comparisons and references.

- Do not force narrative prose where a table would be clearer.

### Callouts

Use GitHub callouts sparingly:

```md

> [!NOTE]

> Additional context that helps understanding.

> [!TIP]

> A practical recommendation.

> [!IMPORTANT]

> Information required for correct operation.

> [!WARNING]

> A risk that can cause data loss, security exposure, or production failure.

```

Do not use callouts for ordinary sentences.

### Code blocks

- Always specify the language when possible.

- Commands must be copy-ready.

- Keep comments inside command blocks minimal.

- State the required working directory.

- Separate alternative execution methods.

- Never include real secrets.

- Use placeholders that are visually explicit, such as `<your-domain>`.

### Links

- Prefer relative links for repository files.

- Use descriptive link text.

- Verify every internal link after restructuring documentation.

- Do not leave links to deleted or renamed files.

- Prefer authoritative external documentation.

### Tables

- Use tables when they improve scanning.

- Keep cells concise.

- Avoid very wide tables that are difficult to read on GitHub.

- Do not use tables for long prose.

### Emojis and icons

- Use them only as light navigation aids.

- Keep naming consistent.

- Never depend on emojis to communicate technical meaning.

- Prefer clear text over decorative symbols.

---

## Documentation correctness rules

### Commands

For every documented command:

- verify that the referenced file, service, script, or target exists,

- verify the package manager,

- verify the working directory,

- verify required prerequisites,

- verify flags,

- verify the expected result.

Where execution is safe and available, run the command.

When a command cannot be executed, state that it was statically verified but not run.

### Environment variables

Cross-check documentation against:

- configuration code,

- `.env.example`,

- Compose files,

- CI workflows,

- deployment configuration.

Document required variables consistently.

Never document secrets using real production values.

### API documentation

Do not manually duplicate the complete API contract when generated OpenAPI documentation is available.

Instead:

- explain the API's purpose,

- document authentication,

- document important workflows,

- link to OpenAPI or generated reference,

- document non-obvious operational constraints.

Manual endpoint examples must match current routes, methods, payloads, and status codes.

### Test documentation

Cross-check test instructions against:

- test configuration,

- package scripts,

- Makefile or task runner,

- CI workflows,

- container service names.

Do not state an exact test count unless explicitly requested and verified at the time of writing.

### Deployment documentation

Cross-check deployment instructions against:

- CI/CD workflows,

- platform configuration,

- Dockerfiles,

- Compose files,

- migration commands,

- readiness checks.

Differentiate clearly between:

- local development,

- staging,

- production.

### Security documentation

Do not expose:

- access tokens,

- passwords,

- private keys,

- webhook signing secrets,

- internal credentials,

- private customer data.

Document safe placeholders and secret-management locations instead.

---

## Rules for updating documentation with code changes

Update documentation in the same task when a change affects:

- user-visible behavior,

- API contracts,

- configuration,

- environment variables,

- installation,

- local development,

- commands,

- database migrations,

- deployment,

- security,

- observability,

- testing strategy,

- architecture,

- supported integrations,

- known limitations.

A code change is not complete when its relevant documentation is stale.

Do not update documentation for internal refactors that do not change how users or developers interact with the system, unless architectural documentation becomes inaccurate.

---

## Documentation cleanup rules

When reorganizing documentation:

1. Identify the canonical document for each topic.

2. Merge useful unique content into the canonical document.

3. Update incoming links.

4. Remove obsolete duplicates.

5. Preserve relevant historical decisions in ADRs or an archive.

6. Confirm no active workflow references deleted files.

7. Confirm the README and documentation index reference only existing files.

Do not keep files only because they already exist.

Do not create files such as `FINAL_REPORT.md`, `AUDIT_FINAL_V2.md`, or timestamped status reports in the repository root unless explicitly required.

Temporary audit reports should not become permanent project documentation by default.

---

## Roadmap and technical debt

### Roadmap

A roadmap should contain future work, not completed implementation history.

Each roadmap item should include, where useful:

- identifier,

- objective,

- scope,

- acceptance criteria,

- dependencies,

- status.

Move completed work to release notes, changelog, or project history when appropriate.

### Technical debt

Technical debt entries should be actionable.

Each item should include:

- problem,

- evidence,

- impact,

- recommended resolution,

- priority,

- affected files or components,

- validation criteria.

Do not use `TECH_DEBT.md` as a generic list of ideas.

---

## Architecture Decision Records

Use ADRs for significant decisions involving:

- system boundaries,

- persistence strategy,

- authentication model,

- integration strategy,

- deployment architecture,

- major dependency choices,

- removal of a major subsystem,

- long-term operational tradeoffs.

Recommended ADR structure:

```md

# ADR-NNNN: Decision title

- Status: Proposed | Accepted | Superseded | Rejected

- Date: YYYY-MM-DD

- Supersedes: ADR-NNNN, when applicable

## Context

## Decision

## Consequences

## Alternatives considered

```

Do not rewrite accepted ADR history to make it appear that the current decision was always obvious.

---

## Validation checklist

Before finishing documentation work, verify:

- [ ] The README describes the current project.

- [ ] The first screen explains the project's purpose.

- [ ] Claims are supported by code or configuration.

- [ ] Commands use the correct package manager and working directory.

- [ ] Quick-start instructions are complete.

- [ ] Environment variables match code and `.env.example`.

- [ ] Test commands match the current test setup.

- [ ] Deployment instructions match actual automation.

- [ ] Internal links resolve.

- [ ] Referenced files exist.

- [ ] Badges resolve and reference real workflows.

- [ ] Diagrams match the implemented architecture.

- [ ] Planned work is separated from completed work.

- [ ] Known limitations are visible.

- [ ] Duplicate or obsolete documentation was removed or archived.

- [ ] No secrets or personal data were added.

- [ ] Markdown formatting renders correctly on GitHub.

- [ ] Documentation index is current.

- [ ] Detailed content is not unnecessarily duplicated in the README.

Run existing documentation checks, Markdown linting, link checking, or repository validation commands when available.

---

## Required final report

After documentation work, provide a concise report containing:

### Summary

- what was audited,

- what was updated,

- the resulting documentation structure.

### Files changed

For each changed file, state its purpose and the important change.

### Cleanup

List:

- merged documents,

- archived documents,

- deleted obsolete documents,

- repaired links.

### Verification

State:

- commands executed,

- checks passed,

- links or facts verified statically,

- checks that could not be run.

### Remaining gaps

List only real unresolved issues, missing information, or documentation risks.

Do not claim full verification when checks were not executed.

---

## Definition of done

Documentation work is complete only when:

1. A new reader can understand the project quickly.

2. A developer can start the project using documented commands.

3. Test and quality instructions match the repository.

4. Configuration and deployment instructions match the implementation.

5. Detailed documentation has a clear index.

6. No active document knowingly contradicts the code.

7. Obsolete and duplicate documentation has been removed, merged, or clearly archived.

8. All material claims are verified.

9. Documentation renders cleanly on GitHub.

10. The final report distinguishes verified facts from assumptions.

