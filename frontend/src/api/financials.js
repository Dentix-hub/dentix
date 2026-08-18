import { api } from './apiClient';

export const getProcedureFinancials = (procedureId) => {
    return api.get(`/api/v1/financials/procedure/${procedureId}/analysis`);
};

export const getAllProceduresFinancials = () => {
    return api.get('/api/v1/financials/procedures/analysis');
};

// Reports
export const getDoctorRevenue = (start, end) => api.get('/api/v1/accounting/doctor-revenue', { params: { start_date: start, end_date: end } });
export const getMyDoctorRevenue = (start, end) => api.get('/api/v1/accounting/doctor-revenue/me', { params: { start_date: start, end_date: end } });
export const getDoctorDetails = (id, start, end) => api.get(`/api/v1/accounting/doctor-details/${id}`, { params: { start_date: start, end_date: end } });
export const getMyDoctorDetails = (start, end) => api.get('/api/v1/accounting/doctor-details/me', { params: { start_date: start, end_date: end } });
export const updateStaffCompensation = (userId, commission, salary, perAppointment = 0) => api.put(`/api/v1/accounting/staff-compensation/${userId}`, null, { params: { commission_percent: commission, fixed_salary: salary, per_appointment_fee: perAppointment } });
export const updateDoctorCompensation = (doctorId, data) => updateStaffCompensation(doctorId, data.commission_percent, data.fixed_salary, data.per_appointment_fee || 0);
export const getStaffRevenue = (start, end) => api.get('/api/v1/accounting/staff-revenue', { params: { start_date: start, end_date: end } });
export const getComprehensiveStats = (start, end, patientId = null) => {
    const params = { start_date: start, end_date: end };
    if (patientId) params.patient_id = patientId;
    return api.get('/api/v1/accounting/comprehensive-stats', { params });
};
export const getPatientsReport = (params) => api.get('/api/v1/accounting/patients-report', { params });
export const getPatientReportDetails = (patientId, params) => api.get(`/api/v1/accounting/patient-report-details/${patientId}`, { params });

// Salary Payments
export const getSalariesStatus = (month) => api.get('/api/v1/accounting/salaries', { params: { month } });
export const recordSalaryPayment = (userId, month, amount, isPartial = false, daysWorked = null, notes = null) =>
    api.post('/api/v1/accounting/salaries', null, { params: { user_id: userId, month, amount, is_partial: isPartial, days_worked: daysWorked, notes } });
export const deleteSalaryPayment = (paymentId) => api.delete(`/api/v1/accounting/salaries/${paymentId}`);
export const updateHireDate = (userId, hireDate) => api.put(`/api/v1/accounting/staff/${userId}/hire-date`, null, { params: { hire_date: hireDate } });

// Trends — exact selected dates are optional for backwards compatibility.
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
