
# AI Module Architecture

This module implements the Enterprise AI Agent for the Smart Clinic system.

## Structure
- **agent/**: Core logic (Orchestration, Prompting, Routing).
- **tools/**: Tool definitions and registry.
- **analytics/**: Usage tracking and cost analysis.
- **memory/**: RAG and context management.
- **config.py**: Centralized configuration.

## Key Features
1. **Smart Routing**: Routes complex queries to `llama-3.3-70b` and simple ones to `llama-3.1-8b`.
2. **Security**:
   - Strict Role-Based Access Control (RBAC) per tool.
   - Input validation using regex and type checking.
   - Rate limiting per tenant (Token Bucket).
3. **Analytics**:
   - Accurate cost estimation based on tokens.
   - Drill-down by tool and user.

## Adding a New Tool
1. Define the tool in `backend/ai/tools/definitions.py`.
2. Register it in `register_default_tools`.
3. Ensure `allowed_roles` are correct.
