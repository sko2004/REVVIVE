# Step 0 — Vayu AI Studio Workspace

**Do-It** › **Vayu AI Studio Workspace** · `00_vayu_workspace/`

Welcome to the **Do-It** project! This step guides you through creating and preparing a **Vayu AI Studio** workspace for the agent modules and Streamlit app.

---

## Quick Navigation

| | |
|:--:|:--:|
| **⬅ Previous** | [Do-It overview](../README.md) |
| **➡ Next** | [Step 1 — Vayu Vector DB →](../01_vayu_vector_databases/) |

---

## Workspace Overview

![Vayu AI Studio Workspace Overview](../assets/workspaces.png)

---

## Open Workspace

Go to [Vayu AI Studio Workspace](https://ipcloud.tatacommunications.com/aistudio/#/build/workspace-list).

For the full create wizard (Start → Infrastructure → Configure Compute and Storage → Observability → Review), see the [Creating Workspace guide](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/workspace/#creating-workspace).

---

## Get Started

1. **Create a Vayu AI Studio workspace**

   - Log in to [Vayu AI Studio](https://ipcloud.tatacommunications.com/aistudio/#/build/workspace-list).
   - Click **Create Workspace** and follow the prompts. See the [Creating Workspace guide](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/workspace/#creating-workspace) for step-by-step wizard details.
   - Make sure **Enable Docker in the Workspace** is turned on before you finish creating the workspace (required for [Step 5](../05_build_app/) and [Step 6](../06_deploy/)).

2. **Import this repository**

   Clone or upload the `do-it` repository into your new workspace:

   ```bash
   git clone https://github.com/your-org/do-it.git
   ```

   Or upload it manually via the UI.

3. **Install Python dependencies**

   Inside your workspace terminal:

   ```bash
   cd do-it
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

   cp .env.example .env
   # Edit .env with credentials from Steps 1–3
   ```

4. **Where to work**

   Use this workspace when working on:

   - [01_vayu_vector_databases/ — Vayu Vector DB](../01_vayu_vector_databases/)
   - [02_vayu_postgres/ — Vayu Managed PostgreSQL](../02_vayu_postgres/)
   - [04_starter_kit/ — Agent modules](../04_starter_kit/)
   - [05_build_app/ — Streamlit UI & deploy](../05_build_app/)

---

## Resources

| Resource | Link |
|----------|------|
| Vayu AI Studio | [Workspace Dashboard](https://ipcloud.tatacommunications.com/aistudio/#/build/workspace-list) |
| Documentation | [Workspace documentation](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/workspace/) |

---

## Navigation

| | |
|:--:|:--:|
| **⬅ Previous** | [Do-It overview](../README.md) |
| **➡ Next** | [Step 1 — Vayu Vector DB →](../01_vayu_vector_databases/) |
| **Overview** | [Do-It overview](../README.md) |
