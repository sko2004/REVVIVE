# Step 3 — Vayu Model as a Service

**Do-It** › **Vayu Model as a Service** · `03_vayu_model_as_a_service/`

| | |
|---|---|
| **Previous** | [← Step 2 — Vayu Managed PostgreSQL](../02_vayu_postgres/) |
| **Next** | [Step 4 — Agent starter kit →](../04_starter_kit/) |

Set up **Vayu Model as a Service** to power your agent's reasoning, tool calling, and planning capabilities.

---

## Quick Setup

### 1. Explore and pick models

Open the **Explore Models** tab in the Model as a Service catalog:

[Explore Models](https://ai-gateway.cloudservices.tatacommunications.com/models/models/explore)

Choose a **chat / LLM model** that supports function/tool calling — this is the "brain" of your agent.

You will get the exact model ID in step 3 via the `/v1/models` API.

### 2. Create API key

Open the **Secret Key** list:

[API keys — Secret Key list](https://ai-gateway.cloudservices.tatacommunications.com/models/models/user/secret-key-list)

Click **Create API key** for your chosen chat model. This maps to `OPENAI_API_KEY` in `.env`.

### 3. Get model ID

Call the `/v1/models` endpoint on your **OpenAI-compatible base URL**, using your API key:

```bash
curl https://models.cloudservices.tatacommunications.com/v1/models \
  -H "Authorization: Bearer <YOUR_API_KEY>"
```

Replace `<YOUR_API_KEY>` with the key you created in step 2. From the response, pick the model ID that matches your choice from step 1 and set it as `CHAT_MODEL` in `.env`.

If your tenant uses a different host, use your `OPENAI_BASE_URL` value instead (e.g. `"${OPENAI_BASE_URL}/models"`).

### 4. Configure `.env`

At the **do-it** repo root, copy `.env.example` to `.env` and set:

```bash
cd do-it
cp .env.example .env
```

| Variable | Value |
|----------|--------|
| `OPENAI_BASE_URL` | Your MaaS OpenAI-compatible base URL (e.g. `https://models.cloudservices.tatacommunications.com/v1`) |
| `OPENAI_API_KEY` | API key created for your **chat** model |
| `CHAT_MODEL` | Chat model ID from the `/v1/models` response (step 3) |

These variables are used by `04_starter_kit/` and `05_build_app/`.

### 5. Continue

Go to [Step 4 — Agent starter kit →](../04_starter_kit/) to implement and test your agent logic.

---

## Key Points

- **Tool calling:** Ensure your chosen model supports function/tool calling — this is critical for `agent_tools.py`.
- **Agent reasoning:** For complex multi-step errands, choose a highly capable chat model.
- **Security:** Never commit API keys to version control — set them only in `do-it/.env`.

---

## Navigation

| | |
|---|---|
| **Previous** | [← Step 2 — Vayu Managed PostgreSQL](../02_vayu_postgres/) |
| **Next** | [Step 4 — Agent starter kit →](../04_starter_kit/) |
| **Overview** | [Do-It overview](../README.md) |
