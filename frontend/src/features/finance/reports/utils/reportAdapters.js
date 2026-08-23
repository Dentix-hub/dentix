/**
 * Explicit response-to-view-model adapters for Finance V2 Reports.
 * Financial truth is server-owned: adapters normalize names/types only and do
 * not recreate profit, deduction, balance, or receivable formulas in React.
 */

export function adaptComprehensiveStats(raw = {}) {
    const period = raw?.period || {};
    const income = raw?.income || {};
    const deductions = raw?.deductions || {};

    return {
        period: {
            start: period.start || '',
            end: period.end || '',
            timezone: period.timezone || '',
            scope: period.scope || 'period',
        },
        definition_version: raw?.definition_version || '',
        currency: raw?.currency || 'EGP',
        invoiced_revenue: Number(income.gross_revenue ?? 0),
        total_discounts: Number(income.total_discounts ?? 0),
        net_production: Number(income.net_revenue ?? income.total_revenue ?? 0),
        collected_revenue: Number(income.total_collected ?? 0),
        manual_expenses: Number(deductions.expenses ?? 0),
        lab_costs: Number(deductions.lab_costs ?? 0),
        doctor_dues: Number(deductions.doctor_dues?.total ?? 0),
        staff_dues: Number(deductions.staff_dues?.total ?? 0),
        total_deductions: Number(deductions.total_deductions ?? 0),
        net_profit: Number(raw?.net_operational_result ?? raw?.net_profit ?? 0),
        all_time_outstanding: Number(
            income.all_time_outstanding ?? income.outstanding ?? 0,
        ),
        period_balance: Number(income.period_balance ?? 0),
        total_appointments: Number(income.total_appointments ?? 0),
        unique_patients: Number(income.unique_patients ?? 0),
    };
}

export function adaptPatientsReport(raw = {}) {
    const patientsList = Array.isArray(raw?.patients) ? raw.patients : [];
    const totalCount = Number(raw?.total ?? patientsList.length);

    const patients = patientsList.map((p) => ({
        patient_id: p.patient_id || p.id,
        file_number: p.file_number || p.patient_id,
        patient_name: p.patient_name || p.name || '—',
        patient_phone: p.patient_phone || p.phone || '',
        invoiced_in_period: Number(p.total_invoiced ?? 0),
        paid_in_period: Number(p.total_paid ?? 0),
        period_balance: Number(p.outstanding_balance ?? 0),
        all_time_outstanding: Number(p.all_time_outstanding ?? 0),
    }));

    // Never derive aggregate cards from the currently loaded page. The server
    // summary is tenant/query scoped and independent of pagination.
    const summary = {
        total_invoiced: Number(raw?.summary?.total_invoiced ?? 0),
        total_paid: Number(raw?.summary?.total_paid ?? 0),
        period_balance: Number(raw?.summary?.period_balance ?? 0),
        total_outstanding: Number(raw?.summary?.total_outstanding ?? 0),
        total_outstanding_scope:
            raw?.summary?.total_outstanding_scope || 'all_time_as_of_now',
    };

    return {
        total: totalCount,
        summary,
        patients,
    };
}

export function adaptExpensesReport(raw) {
    const rawList = Array.isArray(raw) ? raw : Array.isArray(raw?.items) ? raw.items : [];
    return rawList.map((e) => ({
        id: e.id,
        category: e.category || 'عام / متنوع',
        amount: Number(e.cost !== undefined ? e.cost : e.amount || 0),
        item_name: e.item_name || '',
        notes: e.notes || e.description || '',
        date: e.date || '',
        source: e.source || e.provenance || 'manual_expense',
    }));
}

export function adaptProvidersReport(raw) {
    const rawDoctors = Array.isArray(raw)
        ? raw
        : Array.isArray(raw?.doctors)
        ? raw.doctors
        : Array.isArray(raw?.data?.doctors)
        ? raw.data.doctors
        : [];

    return rawDoctors.map((d) => ({
        doctor_id: d.doctor_id || d.id,
        doctor_name: d.doctor_name || d.name || '—',
        treatments: Number(d.treatments || d.treatment_count || 0),
        revenue: Number(d.revenue || 0),
        collected: Number(d.collected || 0),
        lab_cost: Number(d.lab_cost || 0),
        commission_percent: Number(d.commission_percent || 0),
        commission_amount: Number(d.commission_amount || 0),
        fixed_salary: Number(d.fixed_salary || 0),
        fixed_salary_period: Number(
            d.fixed_salary_period !== undefined ? d.fixed_salary_period : d.fixed_salary || 0
        ),
        total_due: Number(d.total_due || 0),
    }));
}

export function adaptProfitabilityReport(raw) {
    const rawProcs = Array.isArray(raw)
        ? raw
        : Array.isArray(raw?.procedures)
        ? raw.procedures
        : [];

    return rawProcs.map((p) => ({
        id: p.id || p.procedure_id,
        name: p.name || p.procedure_name || '—',
        category: p.category || 'عام',
        price: Number(p.price ?? p.base_price ?? 0),
        material_cost: Number(p.material_cost ?? p.cost ?? 0),
        profit_margin: Number(p.profit_margin ?? 0),
        margin_percent: Number(p.margin_percent ?? p.profit_margin_percent ?? 0),
        coverage: p.coverage || p.cost_coverage || null,
        confidence: p.confidence || null,
        completeness: p.completeness || null,
    }));
}
