/**
 * Explicit response-to-view-model adapters for Finance V2 Reports (§18 MASTER_SPEC, GEMINI_REPAIR_PLAN R1).
 * Translates backend StandardResponse payloads into strongly-typed canonical view models.
 */

export function adaptComprehensiveStats(raw = {}) {
    const period = raw?.period || {};
    const income = raw?.income || {};
    const deductions = raw?.deductions || {};

    const netProduction = Number(income.net_revenue ?? income.total_revenue ?? 0);
    const discounts = Number(income.total_discounts || 0);
    const invoiced = Number(income.gross_revenue ?? (netProduction + discounts));
    const collected = Number(income.total_collected || 0);
    const manualExpenses = Number(deductions.expenses || 0);
    const labCosts = Number(deductions.lab_costs || 0);
    const doctorDues = Number(deductions.doctor_dues?.total || 0);
    const staffDues = Number(deductions.staff_dues?.total || 0);

    const totalDeductions = Number(
        deductions.total_deductions || (manualExpenses + labCosts + doctorDues + staffDues)
    );
    const netProfit = Number(raw?.net_profit !== undefined ? raw.net_profit : (collected - totalDeductions));
    const allTimeOutstanding = Number(income.all_time_outstanding || income.outstanding || 0);
    const periodBalance = Number(income.period_balance || (invoiced - collected));

    return {
        period: {
            start: period.start || '',
            end: period.end || '',
        },
        invoiced_revenue: invoiced,
        total_discounts: discounts,
        net_production: netProduction,
        collected_revenue: collected,
        manual_expenses: manualExpenses,
        lab_costs: labCosts,
        doctor_dues: doctorDues,
        staff_dues: staffDues,
        total_deductions: totalDeductions,
        net_profit: netProfit,
        all_time_outstanding: allTimeOutstanding,
        period_balance: periodBalance,
        total_appointments: Number(income.total_appointments || 0),
        unique_patients: Number(income.unique_patients || 0),
    };
}

export function adaptPatientsReport(raw = {}) {
    const patientsList = Array.isArray(raw?.patients) ? raw.patients : [];
    const totalCount = Number(raw?.total || patientsList.length);

    const patients = patientsList.map((p) => {
        const invoiced = Number(p.total_invoiced || 0);
        const paid = Number(p.total_paid || 0);
        const periodBalance = Number(p.outstanding_balance !== undefined ? p.outstanding_balance : (invoiced - paid));
        const allTimeOutstanding = Number(p.all_time_outstanding || 0);

        return {
            patient_id: p.patient_id || p.id,
            file_number: p.file_number || p.patient_id,
            patient_name: p.patient_name || p.name || '—',
            patient_phone: p.patient_phone || p.phone || '',
            invoiced_in_period: invoiced,
            paid_in_period: paid,
            period_balance: periodBalance,
            all_time_outstanding: allTimeOutstanding,
        };
    });

    const calculatedSummary = {
        total_invoiced: patients.reduce((sum, p) => sum + p.invoiced_in_period, 0),
        total_paid: patients.reduce((sum, p) => sum + p.paid_in_period, 0),
        period_balance: patients.reduce((sum, p) => sum + p.period_balance, 0),
        total_outstanding: patients.reduce((sum, p) => sum + p.all_time_outstanding, 0),
    };
    const summary = raw?.summary
        ? {
            total_invoiced: Number(raw.summary.total_invoiced || 0),
            total_paid: Number(raw.summary.total_paid || 0),
            period_balance: Number(raw.summary.period_balance || 0),
            total_outstanding: Number(raw.summary.total_outstanding || 0),
        }
        : calculatedSummary;

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
        total_due: Number(d.total_due || 0),
    }));
}

export function adaptProfitabilityReport(raw) {
    const rawProcs = Array.isArray(raw)
        ? raw
        : Array.isArray(raw?.procedures)
        ? raw.procedures
        : [];

    return rawProcs.map((p) => {
        const price = Number(p.price || p.base_price || 0);
        const cost = Number(p.material_cost !== undefined ? p.material_cost : p.cost || 0);
        const margin = Number(p.profit_margin !== undefined ? p.profit_margin : (price - cost));
        const marginPercent = Number(p.margin_percent !== undefined ? p.margin_percent : p.profit_margin_percent || 0);

        return {
            id: p.id || p.procedure_id,
            name: p.name || p.procedure_name || '—',
            category: p.category || 'عام',
            price,
            material_cost: cost,
            profit_margin: margin,
            margin_percent: marginPercent,
        };
    });
}
