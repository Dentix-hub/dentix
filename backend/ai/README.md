
# AI Module Architecture

This module implements the Enterprise AI Agent for the Smart Clinic system.

## Structure
- **agent/**: Core logic (Orchestration, Prompting, Routing).
- **tools/**: Tool definitions and registry.
- **analytics/**: Usage tracking and cost analysis.
- **memory/**: RAG and context management.
- **config.py**: Centralized configuration.

## Key Features
1. **Smart Routing**: Routes complex queries and Scribe to `openai/gpt-oss-120b`, and simple queries/direct analysis to `openai/gpt-oss-20b`. Override with `GROQ_COMPLEX_MODEL` / `GROQ_FAST_MODEL` for models available to your account. Groq restricted the former Llama defaults to enterprise contracts in August 2026; `llama3-70b-8192` is retired. See [Groq deprecations](https://console.groq.com/docs/deprecations).
2. **Security**:
   - Strict Role-Based Access Control (RBAC) per tool.
   - Input validation using regex and type checking.
   - Rate limiting per tenant (Token Bucket).
3. **Analytics**:
   - Accurate cost estimation based on tokens.
   - Drill-down by tool and user.

Provider model selection does not change commercial request quotas or recorded
costs. The existing analytics fallback keeps its legacy blended estimate; the
new model cards are provider metadata, not a rebilling of historical requests.
External calls still require `GROQ_API_KEY` and the existing approved egress
policy. Changing model defaults does not enable clinical data transmission.

## Adding a New Tool
1. Define the tool in `backend/ai/tools/definitions.py`.
2. Register it in `register_default_tools`.
3. Ensure `allowed_roles` are correct.
