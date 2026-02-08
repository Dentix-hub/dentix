import logging
from fastapi import APIRouter, Depends, HTTPException, Query

logger = logging.getLogger(__name__)
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case
from typing import Optional, List
from datetime import datetime, timedelta

from ..database import get_db
from .. import models
from .auth import get_current_user
from ..constants import ROLES
from backend.services.cost_engine import CostEngine

router = APIRouter(prefix="/admin/ai", tags=["AI Analytics"])

def ensure_super_admin(user: models.User):
    if user.role != ROLES.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

@router.get("/stats")
def get_ai_stats(
    period: str = "24h",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get generic health stats for AI services.
    Phase 1: Visibility First.
    """
    ensure_super_admin(current_user)
    
    # Calculate time range
    now = datetime.utcnow()
    if period == "24h":
        start_time = now - timedelta(hours=24)
    elif period == "7d":
        start_time = now - timedelta(days=7)
    elif period == "30d":
        start_time = now - timedelta(days=30)
    else:
        start_time = now - timedelta(hours=24) # Default

    # Base Query
    query = db.query(models.AILog).filter(models.AILog.timestamp >= start_time)
    
    total_requests = query.count()
    
    # Success Rate
    success_count = query.filter(models.AILog.status == "SUCCESS").count()
    success_rate = (success_count / total_requests * 100) if total_requests > 0 else 100
    
    # Avg Latency
    avg_latency = query.with_entities(func.avg(models.AILog.execution_time_ms)).scalar() or 0
    
    # Token Usage
    total_tokens = query.with_entities(
        func.sum(models.AILog.tokens_in) + func.sum(models.AILog.tokens_out)
    ).scalar() or 0

    return {
        "period": period,
        "total_requests": total_requests,
        "success_rate": round(success_rate, 1),
        "avg_latency_ms": int(avg_latency),
        "total_tokens": total_tokens
    }

@router.get("/intents")
def get_intent_analytics(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Group performance by Intent/Tool.
    Phase 1: Identify bottlenecks.
    """
    ensure_super_admin(current_user)
    
    # Group by tool/intent
    # Select tool, count(*), avg(latency), sum(status=failure)
    # SQLAlchemy grouping
    
    # Safe aggregation
    stats = db.query(
        models.AILog.tool,
        func.count(models.AILog.id).label("count"),
        func.avg(models.AILog.execution_time_ms).label("avg_latency"),
        func.sum(case((models.AILog.status != 'SUCCESS', 1), else_=0)).label("failure_count")
    ).group_by(models.AILog.tool).order_by(desc("count")).limit(10).all()
    
    result = []
    for tool, count, latency, failures in stats:
        tool_name = tool if tool else "chat_unknown"
        fail_count = failures if failures else 0
        fail_rate = (fail_count / count * 100) if count > 0 else 0
        
        result.append({
            "intent": tool_name,
            "usage": count,
            "avg_latency": int(latency or 0),
            "failure_rate": round(fail_rate, 1)
        })
        
    return result

@router.get("/failures")
def get_failure_analytics(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Phase 2: Failure Analysis Engine.
    Aggregates errors by type and tool.
    """
    ensure_super_admin(current_user)
    
    # 1. Breakdown by Error Type
    error_stats = db.query(
        models.AILog.error_type,
        func.count(models.AILog.id).label("count")
    ).filter(
        models.AILog.status != "SUCCESS",
        models.AILog.error_type.isnot(None)
    ).group_by(models.AILog.error_type).all()
    
    # 2. Breakdown by Tool (where status=FAILURE)
    tool_failures = db.query(
        models.AILog.tool,
        func.count(models.AILog.id).label("count")
    ).filter(
        models.AILog.status != "SUCCESS"
    ).group_by(models.AILog.tool).order_by(desc("count")).limit(5).all()
    
    return {
        "by_type": [{"type": e[0] or "unknown", "count": e[1]} for e in error_stats],
        "by_tool": [{"tool": t[0] or "chat", "count": t[1]} for t in tool_failures]
    }

@router.get("/heatmap")
def get_confidence_heatmap(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Phase 2: Confidence Heatmap.
    Returns matrix of Intent vs Confidence Range.
    Ranges: Low (0-0.4), Medium (0.4-0.7), High (0.7-1.0)
    """
    ensure_super_admin(current_user)
    
    # We need to manually bucket or use a complex query. 
    # For MVP (SQLite/Postgres compat), fetching raw aggregates is safer.
    
    # Intent | Confidence | Count
    # Actually just filtering is easier for now:
    
    results = db.query(
        models.AILog.tool,
        models.AILog.confidence
    ).filter(models.AILog.tool.isnot(None)).limit(1000).all()
    
    heatmap = {} # { intent: { low: 0, medium: 0, high: 0 } }
    
    for row in results:
        intent = row.tool
        conf = row.confidence or 0.0
        
        if intent not in heatmap:
            heatmap[intent] = {"low": 0, "medium": 0, "high": 0}
            
        if conf < 0.4:
            heatmap[intent]["low"] += 1
        elif conf < 0.7:
            heatmap[intent]["medium"] += 1
        else:
            heatmap[intent]["high"] += 1
            
    # Format for Frontend: [{intent, low, medium, high}]
    formatted = []
    for k, v in heatmap.items():
        if v["low"] + v["medium"] + v["high"] > 0: # Only active intents
            formatted.append({
                "intent": k,
                "low": v["low"],
                "medium": v["medium"],
                "high": v["high"]
            })
            
    return formatted

@router.get("/costs")
def get_cost_analytics(
    period: str = "30d",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Phase 3: Cost & ROI Intelligence.
    Tracks Token Usage, Estimated Cost, and "Saved Time" ROI.
    """
    ensure_super_admin(current_user)
    
    # Calculate time range
    now = datetime.utcnow()
    if period == "24h":
        start_time = now - timedelta(hours=24)
    elif period == "7d":
        start_time = now - timedelta(days=7)
    elif period == "30d":
        start_time = now - timedelta(days=30)
    else:
        start_time = now - timedelta(days=30)

    # 1. Total Usage & Cost
    # Assuming rough cost: $0.05 per 1M tokens (Llama 3 8B is cheap, but let's use a proxy)
    # let's map: Input $0.50 / 1M, Output $1.50 / 1M (Example Pricing)
    INPUT_COST_PER_1M = 0.50
    OUTPUT_COST_PER_1M = 1.50
    
    usage_stats = db.query(
        func.sum(models.AILog.tokens_in).label("total_in"),
        func.sum(models.AILog.tokens_out).label("total_out"),
        func.count(models.AILog.id).label("total_reqs")
    ).filter(models.AILog.timestamp >= start_time).first()
    
    total_in = usage_stats.total_in or 0
    total_out = usage_stats.total_out or 0
    total_reqs = usage_stats.total_reqs or 0
    
    estimated_cost = ((total_in / 1_000_000) * INPUT_COST_PER_1M) + \
                     ((total_out / 1_000_000) * OUTPUT_COST_PER_1M)
                     
    # 2. ROI Calculation (Time Saved)
    # Assumptions: 
    # - Appointment Booking: Saves 3 mins
    # - Patient Creation: Saves 5 mins
    # - General Chat: Saves 1 min
    
    roi_map = {
        "appointment_booking": 3,
        "smart_book_appointment": 3,
        "create_appointment": 3,
        "create_patient": 5,
        "patient_registration": 5,
        "get_patients_with_balance": 2,
        "finance_query": 2
    }
    
    # Get tool usage counts
    tool_counts = db.query(
        models.AILog.tool, 
        func.count(models.AILog.id)
    ).filter(
        models.AILog.timestamp >= start_time,
        models.AILog.status == "SUCCESS"
    ).group_by(models.AILog.tool).all()
    
    minutes_saved = 0
    for tool, count in tool_counts:
        minutes_saved += roi_map.get(tool, 1) * count # Default 1 min
        
    hours_saved = round(minutes_saved / 60, 1)
    money_saved_usd = round(hours_saved * 15, 2) # Assuming $15/hr labor cost
    
    # 3. Daily Trend (Last 7 intervals)
    # ... Simplified for MVP: Just global stats
    
    return {
        "period": period,
        "total_tokens": total_in + total_out,
        "estimated_cost_usd": round(estimated_cost, 4),
        "roi": {
            "hours_saved": hours_saved,
            "money_saved_usd": money_saved_usd,
            "net_benefit_usd": round(money_saved_usd - estimated_cost, 2)
        }
    }

@router.get("/suggestions")
def get_ai_suggestions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Phase 4: AI Improvement Suggestions Engine.
    Analyzes historical data to suggest optimizations.
    """
    ensure_super_admin(current_user)
    
    suggestions = []
    
    # 1. Analyze High Failure Rates
    # Find tools with > 15% failure rate
    tool_stats = db.query(
        models.AILog.tool,
        func.count(models.AILog.id).label("total"),
        func.sum(case((models.AILog.status != 'SUCCESS', 1), else_=0)).label("failures")
    ).group_by(models.AILog.tool).having(func.count(models.AILog.id) > 5).all() # Min 5 requests
    
    for tool, total, failures in tool_stats:
        fail_rate = (failures / total) * 100
        if fail_rate > 15:
            suggestions.append({
                "type": "CRITICAL",
                "tool": tool,
                "message": f"High failure rate detected for '{tool}' ({int(fail_rate)}%).",
                "action": "Check input schema validation or prompt examples.",
                "impact": "Reliability"
            })
            
    # 2. Analyze Latency Bottlenecks
    # Find tools taking > 4000ms on average
    slow_tools = db.query(
        models.AILog.tool,
        func.avg(models.AILog.execution_time_ms).label("avg_time")
    ).group_by(models.AILog.tool).having(func.avg(models.AILog.execution_time_ms) > 4000).all()
    
    for tool, avg_time in slow_tools:
        suggestions.append({
            "type": "WARNING",
            "tool": tool,
            "message": f"Slow response time for '{tool}' (~{int(avg_time/1000)}s).",
            "action": "Consider simplifying the prompt or moving to async processing.",
            "impact": "User Experience"
        })
        
    # 3. Analyze Low Confidence (Ambiguity)
    # If > 20% of requests have low confidence (< 0.6)
    low_conf_tools = db.query(
        models.AILog.tool,
        func.count(models.AILog.id).label("total"),
        func.sum(case((models.AILog.confidence < 0.6, 1), else_=0)).label("low_conf_count")
    ).group_by(models.AILog.tool).having(func.count(models.AILog.id) > 10).all()
    
    for tool, total, low_conf in low_conf_tools:
        low_conf_val = low_conf if low_conf else 0
        low_rate = (low_conf_val / total) * 100 if total > 0 else 0
        if low_rate > 20:
             suggestions.append({
                "type": "OPTIMIZATION",
                "tool": tool,
                "message": f"AI is uncertain about '{tool}' ({int(low_rate)}% Low Confidence).",
                "action": "Add more Few-Shot examples to the system prompt.",
                "impact": "Accuracy"
            })
            
    # 4. Global Suggestion (If generic)
    if not suggestions:
        suggestions.append({
            "type": "INFO",
            "tool": "System",
            "message": "System is performing well. No critical issues detected.",
            "action": "Monitor usage trends for future scaling.",
            "impact": "Maintenance"
        })
        
    return suggestions


@router.get("/governance")
def get_ai_governance(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Phase 5: AI Governance & Safety.
    Returns current safety settings.
    """
    ensure_super_admin(current_user)
    
    defaults = {
        "ai_max_daily_cost": "5.00",
        "ai_sensitive_masking": "true",
        "ai_require_human_review": "false",
        "ai_auto_block_failure": "true"
    }
    
    settings = {}
    for key, default_val in defaults.items():
        setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == key).first()
        settings[key] = setting.value if setting else default_val
        
    return settings

@router.post("/governance")
def update_ai_governance(
    settings: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Phase 5: Update AI Safety Policies.
    """
    ensure_super_admin(current_user)
    
    allowed_keys = [
        "ai_max_daily_cost", 
        "ai_sensitive_masking", 
        "ai_require_human_review", 
        "ai_auto_block_failure"
    ]
    
    updated = {}
    for key, value in settings.items():
        if key in allowed_keys:
            # Check if exists
            setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == key).first()
            if setting:
                setting.value = str(value)
            else:
                new_setting = models.SystemSetting(key=key, value=str(value), description="AI Governance Setting")
                db.add(new_setting)
            updated[key] = str(value)
            
    db.commit()
    return {"status": "success", "updated": updated}

@router.get("/logs")
def get_ai_logs(
    page: int = 1,
    limit: int = 20,
    trace_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Detailed Log Explorer.
    """
    ensure_super_admin(current_user)
    
    query = db.query(models.AILog)
    
    if trace_id:
        query = query.filter(models.AILog.trace_id.ilike(f"%{trace_id}%"))
    if status:
        query = query.filter(models.AILog.status == status)
        
    total = query.count()
    
    logs = query.order_by(desc(models.AILog.timestamp))\
        .offset((page - 1) * limit)\
        .limit(limit)\
        .all()
        
    return {
        "data": [
            {
                "id": log.id,
                "trace_id": log.trace_id,
                "timestamp": log.timestamp,
                "user_id": log.user_id,
                "tenant_id": log.tenant_id,
                "tool": log.tool,
                "status": log.status,
                "latency": log.execution_time_ms,
                "tokens": (log.tokens_in or 0) + (log.tokens_out or 0),
                "error": log.error_type
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "limit": limit
    }

@router.get("/logs/{log_id}")
def get_log_details(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Deep dive into a specific log entry (Payloads).
    """
    ensure_super_admin(current_user)
    
    log = db.query(models.AILog).filter(models.AILog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
        
    return {
        "id": log.id,
        "trace_id": log.trace_id,
        "timestamp": log.timestamp,
        "input_text": log.input_text,
        "output_text": log.output_text,
        "tool_params": log.tool_params,
        "tool_result": log.tool_result,
        "error_details": log.error_details,
        "confidence": log.confidence or 1.0,
        "scribe_mode": log.scribe_mode
    }


# --- Phase 2: Strategic Intelligence ---
from backend.services.ai_service import AIService
from pydantic import BaseModel

class ClinicStats(BaseModel):
    revenue: float
    breakdown: dict
    total_costs: float
    net_profit: float
    margin_percent: float

def get_detailed_analytics(db: Session, tenant_id: int, days: int = 30) -> str:
    """Fetch deep KPIs: Margins, High-Cost procedures, and Efficiency."""
    # Ensure dependencies are available locally if needed, but they are imported at top
    start_date = datetime.utcnow() - timedelta(days=days)
    cost_engine = CostEngine(db, tenant_id)
    
    # 1. Top Procedures by Volume and Net Profitability
    try:
        # Check if is_deleted exists on Treatment
        has_deleted_col = hasattr(models.Treatment, "is_deleted")
        
        top_procs_query = db.query(
            models.Treatment.procedure, 
            func.count(models.Treatment.id).label('proc_count'),
            func.sum(models.Treatment.cost).label('total_revenue')
        ).filter(
            models.Treatment.date >= start_date,
            models.Treatment.tenant_id == tenant_id
        )
        
        if has_deleted_col:
            top_procs_query = top_procs_query.filter(models.Treatment.is_deleted == False)
            
        top_procs = top_procs_query.group_by(models.Treatment.procedure).order_by(desc('proc_count')).limit(5).all()
        
        proc_details = []
        for p in top_procs:
            if not p.procedure: continue
            
            # Find base procedure ID to calculate margin
            proc_obj = db.query(models.Procedure).filter(
                models.Procedure.name == p.procedure,
                models.Procedure.tenant_id == tenant_id
            ).first()
            
            theoretical_margin = 0.0
            if proc_obj:
                try:
                    analysis = cost_engine.calculate_procedure_cost(proc_obj.id)
                    theoretical_margin = analysis.get('margin_percentage', 0.0)
                except Exception:
                    pass
                
            proc_details.append({
                "name": p.procedure,
                "volume": p.proc_count,
                "revenue": p.total_revenue,
                "theoretical_margin": theoretical_margin
            })
    except Exception as e:
        logger.error(f"Error fetching top procedures: {e}")
        proc_details = []

    # 2. Lab Usage vs Revenue
    lab_by_doctor = []
    try:
        # Check if User table has username (Standard) or needs fallback
        # Traceback indicated issues with User attributes previously
        stmt = db.query(
            models.User.username,
            func.sum(models.LabOrder.cost).label('lab_total')
        ).join(models.LabOrder, models.LabOrder.doctor_id == models.User.id).filter(
            models.LabOrder.order_date >= start_date,
            models.LabOrder.tenant_id == tenant_id
        ).group_by(models.User.username)
        
        lab_by_doctor = stmt.all()
    except Exception as e:
        logger.error(f"Error fetching lab usage: {e}")
        lab_by_doctor = []

    # 3. Low Stock Alerts for Critical Materials
    try:
        from backend.models.inventory import Material
        low_stock = db.query(Material.name).filter(
            Material.tenant_id == tenant_id
        ).order_by(Material.alert_threshold.desc()).limit(3).all()
    except Exception:
        low_stock = []

    # BUILD STRING
    details = "\n\n### DEEP KPI ANALYSIS (STRICT DATA):\n"
    
    if proc_details:
        details += "**Procedure Performance & Theoretical Margins:**\n"
        for d in proc_details:
            rev_val = d.get('revenue', 0.0) or 0.0
            margin_val = d.get('theoretical_margin', 0.0) or 0.0
            details += f"- {d['name']}: {d['volume']} sess, ${rev_val:,.0f} Rev, Avg Margin: {margin_val}%\n"
    
    if lab_by_doctor:
        details += "\n**Lab Spend by Doctor:**\n"
        for l in lab_by_doctor:
            try:
                # SAFE ACCESS: Use username if available
                doc_name = getattr(l, 'username', 'Unknown Doctor')
                val = getattr(l, 'lab_total', 0.0) or 0.0
                details += f"- {doc_name}: ${val:,.0f}\n"
            except Exception as e_inner:
                logger.warning(f"Skipping doctor row: {e_inner}")

    if low_stock:
        details += "\n**Critical Supply Monitoring:**\n"
        details += f"- Monitoring: {', '.join([m.name for m in low_stock])}\n"
        
    return details

@router.post("/analyze-clinic")
async def analyze_clinic(
    stats: ClinicStats,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Generate AI insights based on financial stats.
    """
    # ensure_super_admin(current_user) # Optional: Allow Managers?
    
    service = AIService(db, current_user)
    
    # Enrich with deep KPIs
    try:
        detailed_context = get_detailed_analytics(db, current_user.tenant_id)
    except Exception as e:
        logger.error(f"Failed to get detailed context: {e}")
        detailed_context = ""
    
    # Safeguard stats (Pydantic might allow partial data if configured, better safe than 500)
    rev = stats.revenue or 0.0
    exp = stats.breakdown.get('expenses', 0) or 0.0
    lab = stats.breakdown.get('lab_costs', 0) or 0.0
    mat = stats.breakdown.get('material_costs', 0) or 0.0
    profit = stats.net_profit or 0.0
    margin = stats.margin_percent or 0.0

    prompt = f"""
    Act as a senior CLINIC STRATEGIST & CFO. Analyze the following data for the last 30 days:
    
    [TOP LEVEL STATS]
    - Revenue: ${rev:,.0f}
    - Expenses (Rent/Staff): ${exp:,.0f}
    - Lab Fees: ${lab:,.0f}
    - Material Usage (COGS): ${mat:,.0f}
    - Net Profit: ${profit:,.0f} (Global Margin: {margin}%)

    {detailed_context}

    Your goal is to increase NET PROFIT by at least 15%. 
    Be direct, pragmatic, and harsh if numbers look bad.
    
    REQUIRED OUTPUT STRUCTURE:
    1. **Strategic Flaw**: One major problem detected in the numbers.
    2. **High-Value Target**: Which procedure/doctor to push based on margins?
    3. **Cost Leak**: Where is money being wasted (Lab vs Material vs OpEx)?
    4. **Immediate Action**: One thing to do tomorrow.

    Format as a clean Markdown. Language: Arabic.
    """
    
    response = await service.analyze_direct(prompt)
    
    return {"insights": response.message}
