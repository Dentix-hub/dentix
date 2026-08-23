import { api } from './apiClient';

export const getProcedureFinancials = (procedureId) => {
    return api.get(`/api/v1/financials/procedure/${procedureId}/analysis`);
};

export const getAllProceduresFinancials = () => {
    return api.get('/api/v1/financials/procedures/analysis');
};

// Reports / Finance truth
export const getDoctorRevenue = (start, end) => api.get('/api/v1/accounting/doctor-revenue', { params: { start_date: start, end_date: end } });
export const getMyDoctorRevenue = (start, end) => api.get('/api/v1/accounting/doctor-revenue/me', { params: { start_date: start, end_date: end } });
export const getDoctorDetails = (id, start, end) => api.get(`/api/v1/accounting/doctor-details/${id}`, { params: { start_date: start, end_date: end } });
export const getMyDoctorDetails = (start, end) => api.get('/api/v1/accounting/doctor-details/me', { params: { start_date: start, end_date: end } });

export const patchStaffCompensation = (userId, updates) =>
    api.patch(`/api/v1/accounting/staff-compensation/${userId}`, updates);

// Compatibility helper for older callers. Undefined fields are omitted rather
// than being converted to zero.
export const updateStaffCompensation = (userId, commission, salary, perAppointment) => {
    const updates = {};
    if (commission !== undefined) updates.commission_percent = commission;
    if (salary !== undefined) updates.fixed_salary = salary;
    if (perAppointment !== undefined) updates.per_appointment_fee = perAppointment;
    return patchStaffCompensation(userId, updates);
};

export const updateDoctorCompensation = (doctorId, data) =>
    patchStaffCompensation(doctorId, {
        ...(data.commission_percent !== undefined
            ? { commission_percent: data.commission_percent }
            : {}),
        ...(data.fixed_salary !== undefined ? { fixed_salary: data.fixed_salary } : {}),
        ...(data.per_appointment_fee !== undefined
            ? { per_appointment_fee: data.per_appointment_fee }
            : {}),
        ...(data.hire_date !== undefined ? { hire_date: data.hire_date } : {}),
    });

export const getStaffRevenue = (start, end) => api.get('/api/v1/accounting/staff-revenue', { params: { start_date: start, end_date: end } });

export const getFinanceSummary = (start = null, end = null, patientId = null) => {
    const params = {};
    if (start && end) {
        params.start_date = start;
        params.end_date = end;
    }
    if (patientId) params.patient_id = patientId;
    return api.get('/api/v1/accounting/comprehensive-stats', { params });
};

// Compatibility alias while existing consumers migrate to the domain name.
export const getComprehensiveStats = getFinanceSummary;

export const getPatientsReport = (params) => api.get('/api/v1/accounting/patients-report', { params });
export const getPatientReportDetails = (patientId, params) => api.get(`/api/v1/accounting/patient-report-details/${patientId}`, { params });

// Salary Payments
export const getSalariesStatus = (month) => api.get('/api/v1/accounting/salaries', { params: { month } });
export const recordSalaryPayment = (userId, month, amount, isPartial = false, daysWorked = null, notes = null) =>
    api.post('/api/v1/accounting/salaries', null, { params: { user_id: userId, month, amount, is_partial: isPartial, days_worked: daysWorked, notes } });
export const deleteSalaryPayment = (paymentId) => api.delete(`/api/v1/accounting/salaries/${paymentId}`);
export const updateHireDate = (userId, hireDate) =>
    patchStaffCompensation(userId, { hire_date: hireDate });

// Trends — exact selected dates are optional for backwards compatibility.
// This is a time-series endpoint, not the deprecated headline profitability
// source. Headline Finance truth comes from getFinanceSummary().
export const getFinanceProfitabilityTrend = (period = '30d', start = null, end = null) => {
    const params = { period };
    if (start && end) {
        params.start_date = start;
        params.end_date = end;
    }
    return api.get('/api/v1/metrics/profitability/trend', { params });
};

// Activity Feed (§17 MASTER_SPEC, FIN-ACT-001)
export const getFinancialActivity = (params) => api.get('/api/v1/accounting/activity', { params });
