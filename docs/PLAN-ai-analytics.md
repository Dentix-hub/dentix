# Project Plan: AI Analytics & Improvement Engine
> **File**: `docs/PLAN-ai-analytics.md`
> **Goal**: Transform AI Logs from a passive record into a proactive "AI Improvement Engine" for the Super Admin.

## 1. Executive Summary
The **AI Analytics & Improvement Engine** will provide the Super Admin with deep visibility into the system's AI behavior. Unlike simple logging, this system focuses on **health metrics**, **cost analysis**, **failure diagnosis**, and **automated improvement suggestions**.

## 2. Phased Implementation Roadmap

### 🧩 Phase 0: Prerequisites (Unified Log Schema)
**Goal**: Establish a unified, indexed, and consistent data foundation.
- [ ] **Database Schema Upgrade**
  - [ ] Consolidate `AIUsageLog` and `AIAuditLog` into a robust `AILog` table.
  - [ ] Add columns: `trace_id` (UUID), `intent`, `confidence`, `tokens_in/out`, `latency_ms`, `error_type`, `error_stage`.
  - [ ] Add indexes for high-performance querying (`trace_id`, `status`, `created_at`, `intent`).
- [ ] **Strict Logging Policy**
  - [ ] Update `AIService` to enforce logging rules (no log without trace_id).
  - [ ] Ensure `trace_id` propagates through `ToolExecutor` and `Agent` layers.

### 🧩 Phase 1: AI Health Analytics (Visibility)
**Goal**: "At-a-glance" health check for the Super Admin.
- [ ] **Backend: Analytics API** (`/admin/ai/stats`)
  - [ ] Aggregation endpoints for KPIs: Success Rate, Avg Latency, Low Confidence %.
  - [ ] Time-series data for generic charts (24h, 7d, 30d).
- [ ] **Frontend: Dashboard UI**
  - [ ] **KPI Cards**: Vital signs (Success %, Requests/min).
  - [ ] **Intent Table**: Most used intents, failure rates, avg confidence.
  - [ ] **Recent Logs**: Live feed of interactions with "Trace" view.

### 🧩 Phase 2: Failure & Root Cause Analysis
**Goal**: Diagnose *why* things fail.
- [ ] **Backend: Failure Analysis Engine**
  - [ ] Aggregate failures by `error_type` (Validation vs LLM vs Tool).
  - [ ] Group similar failures (Cluster analysis).
- [ ] **Frontend: Diagnostics View**
  - [ ] **Failure Breakdown**: Pie chart of error sources.
  - [ ] **Confidence Heatmap**: Intent vs Confidence bucket.

### 🧩 Phase 3: Decision & Cost Intelligence
**Goal**: Optimize costs and verify AI decision logic.
- [ ] **Decision Path Tracking**
  - [ ] Track hops: `Intent -> Logic -> Tool -> DB`.
  - [ ] Identify unnecessary LLM calls (e.g. "Simple intent" routed to "Complex LLM").
- [ ] **Cost Monitoring**
  - [ ] Calculate approx. cost based on Token usage per Tenant/Model.

### 🧩 Phase 4: AI Improvement Suggestions (The "Brain")
**Goal**: Proactive suggestions to improve the system.
- [ ] **Suggestion Engine** (Rule-based v1)
  - [ ] Detect "High Failure Intent" -> Suggest "Review Prompts".
  - [ ] Detect "Low Confidence consistently" -> Suggest "Add Training Data".
- [ ] **Management UI**
  - [ ] List of suggestions (Apply/Dismiss/Snooze).

### 🧩 Phase 5: Governance & Automation
**Goal**: Safety rails and continuous improvement.
- [ ] **Dataset Export**: One-click export of "Failed Rows" for fine-tuning.
- [ ] **Replay Mode**: Dry-run a failed trace ID to see if code fix resolved it.

## 3. Technical Architecture

### Database Model (`AILog`)
```python
class AILog(Base):
    __tablename__ = "ai_logs"
    trace_id = Column(String, index=True)  # UUID
    tenant_id = Column(Integer, index=True)
    user_id = Column(Integer)
    
    intent = Column(String, index=True)
    action_type = Column(String) # QUERY, TOOL_EXECUTION, CONFIRMATION
    
    input_text = Column(Text)
    output_text = Column(Text)
    tool_calls = Column(JSON)      # Details of tools used
    
    status = Column(String)        # SUCCESS, FAILURE, BLOCKED
    error_type = Column(String)    # VALIDATION, LLM, TOOL, NETWORK
    
    stats = Column(JSON)           # {latency: 450, tokens: 120, confidence: 0.9}
    timestamp = Column(DateTime, default=utcnow)
```

### API Structure
- `GET /admin/ai/dashboard`: Summary stats.
- `GET /admin/ai/logs`: Paginated logs with filters.
- `GET /admin/ai/logs/{trace_id}`: Deep dive details.

## 4. Agent Assignments
- **Senior Backend Dev**: Schema migration (`alembic`), `AIService` refactor, Analytics SQL optimization.
- **Frontend Specialist**: Dashboard UI, Charts (Recharts/Chart.js), Log Inspector Modal.
- **QA/Data Engineer**: Verify data consistency, stress test logging performance.

## 5. Next Steps
1. **Review**: Confirm Phase 0 schema changes.
2. **Execute**: Run `/create implementation of Phase 0`.
3. **Verify**: Ensure logs are flowing correctly before building Dashboard.
