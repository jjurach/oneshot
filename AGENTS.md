# MANDATORY AI Agent Instructions (Condensed)

**CRITICAL:** This document contains the essential, non-negotiable rules for all development tasks. You are responsible for knowing and following every rule here. Detailed explanations, full templates, and non-critical best practices are located in the `/docs` directory.

---

## 1. The Core Workflow

**MANDATORY:** For any request that involves creating or modifying code or infrastructure, you MUST follow this workflow.

**Step A: Analyze the Request & Declare Intent**
1.  **Is it a simple question?** → Answer it directly.
2.  **Is it a Trivial Change?** → Make the change directly. No documentation required.
3.  **Is it anything else?** → Announce you will create a **Project Plan**.

> **Trivial Change Definition:** Non-functional changes like fixing typos in comments or code formatting. The full definition and examples are in `docs/01_overview.md`.

**Step B: Create a Project Plan (If Required)**
- Use the `Project Plan` structure defined in Section 3.
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
- After each logical change, create or update a **Change Documentation** entry in `dev_notes/changes/`. Use the structure from Section 3.

---

## 2. Project Component & Skill Routing Guide

**MANDATORY:** Use this guide to locate project components.

- **`infrastructure/`**: Terraform for AWS ECS deployment.
- **`api/openapi.yaml`**: **The API's single source of truth.** Changes here are critical and must be planned carefully as they impact all frontends and the backend.
- **`docs/`**: Detailed documentation (architecture, conventions, full templates).
- **`dev_notes/`**: All AI-generated Project Plans and Change Documentation.

---

## 2.1. Documentation Index & Quick Reference

Insert project specific information here.

---

## 3. Documentation Structures (Checklists)

**MANDATORY:** All Project Plans and Change Documentation you create must include these sections. Full, detailed templates are in `docs/templates.md`.

### Project Plan Structure
- `# Project Plan: [Project Name]`
- `Objective`
- `Implementation Steps` (Detailed list of actions)
- `Success Criteria`
- `Testing Strategy`
- `Risk Assessment`

### Change Documentation Structure
- `# Change: [Brief Description]`
- `Related Project Plan`
- `Overview` of the change.
- `Files Modified` with a summary of what changed in each.
- `Impact Assessment`

---

## 4. The Unbreakable Rules

1.  **Approval is Mandatory:** This is the most important rule. Never act on a Project Plan without explicit developer approval.
2.  **Quality is Mandatory:** You MUST follow the existing code patterns, conventions, style, and typing of the files you are editing. New code should look like the old code.
3.  **Uncertainty Requires a Full Stop:** If you encounter any error, are confused by a requirement, or are unsure how to proceed, you MUST **STOP** immediately. Document the issue and ask the developer for guidance. Do not try to solve novel problems alone.
4.  **File Naming is Mandatory:** All Project Plans and Change Documentation in `dev_notes/` MUST use the `YYYY-MM-DD_HH-MM-SS_description.md` format.
5.  **Slack Notification (If Supported):** Notify using the slack-notifications MCP service each time you commit to the local git repo. See `docs/06_tools_and_integrations.md` for setup instructions. **Note:** This rule applies only to agents with MCP support (e.g., Claude Code). Agents without MCP capabilities may skip this step.

This condensed file preserves all mandatory instructions while significantly reducing the token count, making it suitable for models with smaller context windows.
