# MANDATORY AI Agent Instructions (Condensed)

**CRITICAL:** This document contains the essential, non-negotiable rules for all development tasks. You are responsible for knowing and following every rule here. Detailed explanations, full templates, and non-critical best practices are located in the `/docs` directory.

---

## 1. The Core Workflow

**MANDATORY:** For any request that involves creating or modifying code or infrastructure, you MUST follow this workflow.

**Step A: Analyze the Request & Declare Intent**
1.  **Is it a simple question?** → Answer it directly.
2.  **Is it a Trivial Change?** → Make the change directly. No documentation required.
3.  **Is it just to fix tests or to fix broken usage?** → Make the change directly. No documentation required.
4.  **Is it a Research/Documentation Change?** → Make the change directly. No extra documentation required.
5.  **Is it anything else?** → Announce you will create a **Project Plan**.

> **Trivial Change Definition:** Non-functional changes like fixing typos in comments or code formatting. The full definition and examples are in `docs/overview.md`.
> **Research/Documentation Change:** Requests which culminate ONLY into writes to markdown documents in the root folder or in docs/ or in `dev_notes`.

**Step B: Create a Project Plan (If Required)**
- Use the **Project Plan Structure** defined in `docs/templates.md`.
- The plan must be detailed enough for another agent to execute.
- Save the plan to `dev_notes/project_plans/YYYY-MM-DD_HH-MM-SS_description.md`.

**Step C: AWAIT DEVELOPER APPROVAL**
- **NEVER EXECUTE A PLAN WITHOUT EXPLICIT APPROVAL.**
- Present the full Project Plan to the developer.
- "Approved", "proceed", "go ahead", "ok", or "yes" mean you can start.
- If the developer asks questions or provides feedback, answer them and then **return to a waiting state** until you receive a new, explicit approval.
- **If approval is ambiguous** (e.g., "maybe", "I think so", "probably"): Ask a follow-up clarifying question such as "I want to confirm: should I proceed with this Project Plan? Please respond with 'yes' or 'no'."

**Step D: Implement & Document Concurrently**
- Execute the approved plan step-by-step.
- After each logical change, create or update a **Change Documentation** entry in `dev_notes/changes/`. Use the structure from `docs/templates.md`.

---

## 2. Documentation & Resources

**MANDATORY:** Use the specific documentation files for details.

- **`docs/overview.md`**: Main index of all documentation.
- **`docs/project-structure.md`**: Locations of project components (Executors, Logic, Tests) and architecture details.
- **`docs/templates.md`**: Mandatory templates for **Project Plans** and **Change Documentation**.
- **`docs/`**: Directory containing all other detailed documentation (e.g., streaming design, executor details).

**Skill Routing:**
- For **Executor** implementation details: See `docs/project-structure.md` and `src/oneshot/providers/`.
- For **Streaming/State** architecture: See `docs/streaming-and-state-management.md`.
- For **Templates**: See `docs/templates.md`.

---

## 3. The Unbreakable Rules

1.  **Approval is Mandatory:** This is the most important rule. Never act on a Project Plan without explicit developer approval.
2.  **Quality is Mandatory:** You MUST follow the existing code patterns, conventions, style, and typing of the files you are editing. New code should look like the old code.
3.  **Uncertainty Requires a Full Stop:** If you encounter any error, are confused by a requirement, or are unsure how to proceed, you MUST **STOP** immediately. Document the issue and ask the developer for guidance. Do not try to solve novel problems alone.
4.  **File Naming is Mandatory:** All Project Plans and Change Documentation in `dev_notes/` MUST use the `YYYY-MM-DD_HH-MM-SS_description.md` format.
5.  **Temporary Files:** NEVER use `/tmp` or system temporary directories for temporary files. Always create temporary files in the current working directory using the naming patterns `tmp-*` or `*.tmp` or `tmp/*`. These files should be cleaned up when no longer needed.
6.  **Slack Notification (If Supported):** Notify using the slack-notifications MCP service each time you commit to the local git repo. **Note:** This rule applies only to agents with MCP support.