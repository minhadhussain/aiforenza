# Security skills installed for AI Forenza

OpenCode discovers these project-local skills from `.opencode/skills/*/SKILL.md`. The setup does not replace the user's global OpenCode configuration.

| Skill | Publisher | Purpose | License |
| --- | --- | --- | --- |
| `security-best-practices` | OpenAI | FastAPI, Next.js, React, and browser security | Apache-2.0 |
| `security-threat-model` | OpenAI | Repository-grounded trust boundaries, abuse paths, and mitigations | Apache-2.0 |
| `supabase-postgres-best-practices` | Supabase | RLS, privileges, SQL constraints, locking, and database access | MIT |
| `property-based-testing` | Trail of Bits | Strong invariants for money, state transitions, parsing, and validation | CC-BY-SA-4.0 |
| `aiforenza-security-review` | This project | Applies the specialist skills to AI Forenza's architecture and financial invariants | Project-authored |

## Provenance and scope

The four downloaded skills are copied from pinned upstream commits. `.opencode/security-skills.lock.json` records their source repositories, paths, commits, Git blob hashes, and normalized-content SHA-256 hashes. Each downloaded directory contains its upstream license.

- OpenAI: <https://github.com/openai/skills>, revision `49f948faa9258a0c61caceaf225e179651397431`.
- Supabase: <https://github.com/supabase/agent-skills>, revision `8331f910845103c08d51f6ca1d86ebb7d1f745e3`.
- Trail of Bits: <https://github.com/trailofbits/skills>, revision `32e34f8173796e3566a51aee877dc96bc5191f64`.

Only skill instructions, applicable references, and licenses are installed. The OpenAI best-practices bundle is limited to this project's FastAPI/Next.js/React/general-frontend references; other language/framework guides are omitted. OpenCode does not need upstream Codex UI metadata. No downloaded scripts, plugins, agents, or hooks are installed/executed. Vendored content is unmodified; the project-specific workflow is a separate skill.

These skills provide guidance rather than an automatic security guarantee. Framework references may describe newer versions than this app uses; check installed versions and current advisories before applying framework-specific recommendations.

## Use

Fully restart OpenCode in the AI Forenza project, then run:

```text
/security-review
```

To request focused fixes as well:

```text
/security-review Audit the whole system, then implement confirmed high-priority fixes and run the relevant regression tests. Preserve paid/promotional billing and reservation invariants.
```

You can also request an individual skill by name in a normal prompt.

## Verify or reproduce installation

```powershell
python tools/install_security_skills.py --check
python tools/verify_security_skills.py
```

For a checkout where these downloaded skill directories are absent, `python tools/install_security_skills.py` installs the pinned documentation bundles. It refuses to overwrite existing skills. It does not read application secrets, change database/security settings, install dependencies, or call inference providers.

Integrity validation treats CRLF and LF as equivalent to support Windows Git checkouts. Original downloaded bytes are verified against the pinned Git blobs during installation.
