import axios from 'axios';
import { getToken, getRefreshToken, setToken, removeToken } from '../utils';

// Dynamically determine API URL
// Dynamically determine API URL
// Build Version: 1.0.5 (Force Refresh)
const getApiUrl = () => {
    // 1. Environment Variable (Production) - Recommended for Vercel
    if (import.meta.env.VITE_API_BASE_URL) {
        return import.meta.env.VITE_API_BASE_URL;
    }

    const hostname = window.location.hostname;
    const protocol = window.location.protocol;

    // 2. Localhost or IP
    if (hostname === 'localhost' || hostname === '127.0.0.1' || /^(\d{1,3}\.){3}\d{1,3}$/.test(hostname)) {
        return `${protocol}//${hostname}:8000`;
    }

    // 3. Same Origin (Hugging Face Spaces, Vercel, or Custom Domains)
    // Using relative URL ensures the frontend hits the backend on the same origin
    return '';
};

export const API_URL = getApiUrl();

// Increase timeout to 30 seconds for uploads
export const api = axios.create({
    baseURL: API_URL,
    timeout: 30000,
});

// Auth
export const login = (username, password) => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    return api.post('/api/v1/auth/token', formData);
};

export const registerClinic = (data) => api.post('/api/v1/auth/register_clinic', data);
export const getMe = () => api.get('/api/v1/users/me');
export const updateProfile = (data) => api.put('/api/v1/users/me', data);

export default api;

// Add Interceptor for Token
api.interceptors.request.use(config => {
    // If this is a retry and we clearly set the header, don't overwrite it with potentially stale storage
    if (config._retry && config.headers.Authorization) {
        return config;
    }

    const token = getToken();
    if (token) {
        if (config.headers && typeof config.headers.set === 'function') {
            config.headers.set('Authorization', `Bearer ${token}`);
        } else {
            config.headers = config.headers || {};
            config.headers.Authorization = `Bearer ${token}`;
        }
    }
    return config;
});

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
    failedQueue.forEach(prom => {
        if (error) {
            prom.reject(error);
        } else {
            prom.resolve(token);
        }
    });

    failedQueue = [];
};

api.interceptors.response.use(
    response => {
        // 1. Handle Blobs (Backups/Exports)
        if (response.data instanceof Blob) {
            return response;
        }

        // 2. Detect and unwrap StandardResponse envelope
        // Unwrap success_response: { success, data, message } → return data directly
        if (response.data && typeof response.data === 'object' && 'success' in response.data && 'data' in response.data) {
            // Attach pagination metadata if it exists
            if (response.data.pagination && response.data.data !== null && typeof response.data.data === 'object') {
                try {
                    Object.defineProperty(response.data.data, '_pagination', {
                        value: response.data.pagination,
                        writable: true,
                        enumerable: false, // Don't show in loops
                        configurable: true
                    });
                } catch (e) {
                    response.data.data._pagination = response.data.pagination;
                }
            }
            // Mutate in-place to avoid breaking references
            response.data = response.data.data;
        }

        return response;
    },
    async error => {
        const originalRequest = error.config;

        // Log detailed error for debugging
        if (error.response) {
            console.error('[API] Request failed:', error.response.status, originalRequest.url);
        }

        if (error.response?.status === 401 && !originalRequest._retry && originalRequest.url !== '/api/v1/token' && originalRequest.url !== '/api/v1/auth/refresh') {

            const debugMsg = error.response?.data?.detail || "Unknown Auth Error";

            if (isRefreshing) {
                return new Promise(function (resolve, reject) {
                    failedQueue.push({ resolve, reject });
                }).then(token => {
                    originalRequest.headers['Authorization'] = 'Bearer ' + token;
                    return api(originalRequest);
                }).catch(err => {
                    return Promise.reject(err);
                });
            }

            originalRequest._retry = true;
            isRefreshing = true;

            const refreshToken = getRefreshToken();

            if (!refreshToken) {
                removeToken();
                window.location.href = '/';
                return Promise.reject(error);
            }

            try {
                // Using axios directly to avoid interceptor loop, but we need baseURL
                // Constructing form data as required by OAuth2
                const formData = new FormData();
                formData.append('refresh_token', refreshToken);

                // Call /auth/refresh
                const response = await axios.post(`${API_URL}/api/v1/auth/refresh`, formData);

                const { access_token, refresh_token: newRefreshToken } = response.data;

                // Detect which storage to use (if session has token, keep using session)
                const isSession = !!sessionStorage.getItem('token');
                setToken(access_token, newRefreshToken, !isSession);
                api.defaults.headers.common['Authorization'] = 'Bearer ' + access_token;
                originalRequest.headers['Authorization'] = 'Bearer ' + access_token;

                processQueue(null, access_token);
                return api(originalRequest);
            } catch (err) {
                processQueue(err, null);
                removeToken();

                const errorDetail = err.response?.data?.detail;
                if (errorDetail && typeof errorDetail === 'string' && (errorDetail.includes('جهاز آخر') || errorDetail.includes('Session Mismatch'))) {
                    window.location.href = '/login?reason=session_mismatch';
                    return new Promise(() => { }); // Prevent boundary crash
                }

                window.location.href = '/';
                return Promise.reject(err);
            } finally {
                isRefreshing = false;
            }
        }

        if (error.response?.status === 500) {
            console.error('[API] Server Error:', error.response?.data?.detail || 'Internal Server Error');
        }

        return Promise.reject(error);
    }
);

// Patients
export const searchPatients = (query) => api.get(`/api/v1/patients/search?q=${query}`);
export const getPatients = () => api.get('/api/v1/patients/');
export const getPatient = (id) => api.get(`/api/v1/patients/${id}`);
export const createPatient = (data) => api.post('/api/v1/patients/', data);
export const updatePatient = (id, data) => api.put(`/api/v1/patients/${id}`, data);
export const deletePatient = (id) => api.delete(`/api/v1/patients/${id}`);

// Appointments
export const getAppointments = () => api.get('/api/v1/appointments/');
export const createAppointment = (data) => api.post('/api/v1/appointments/', data);
export const updateAppointmentStatus = (id, status) => api.put(`/api/v1/appointments/${id}/status?status=${status}`);
export const deleteAppointment = (id) => api.delete(`/api/v1/appointments/${id}`);

// Dental Chart
export const getPatientTeeth = (patientId) => api.get(`/api/v1/patients/${patientId}/tooth_status`);
export const updateToothStatus = (data) => api.post('/api/v1/treatments/tooth_status/', data);

// Treatments
export const getPatientTreatments = (patientId) => api.get(`/api/v1/patients/${patientId}/treatments`);
export const createTreatment = (data) => api.post('/api/v1/treatments/', data);
export const updateTreatment = (id, data) => api.put(`/api/v1/treatments/${id}`, data);
export const deleteTreatment = (id) => api.delete(`/api/v1/treatments/${id}`);
export const addTreatmentSession = (treatmentId, sessionData) => api.post(`/api/v1/treatments/${treatmentId}/sessions`, sessionData);

// Billing
export const createPayment = (data) => api.post('/api/v1/payments/', data);
export const getAllPayments = () => api.get('/api/v1/payments/');
export const getPatientPayments = (patientId) => api.get(`/api/v1/patients/${patientId}/payments`);
export const getFinancialStats = () => api.get('/api/v1/expenses/stats');
export const getDashboardStats = () => api.get('/api/v1/stats/dashboard');
export const getTodayPayments = () => api.get('/api/v1/payments/today/payments');
export const getTodayDebtors = () => api.get('/api/v1/payments/today/debtors');
export const deletePayment = (id) => api.delete(`/api/v1/payments/${id}`);

// Backup
export const downloadBackup = () => api.get('/api/v1/settings/backup/download', { responseType: 'blob' });
export const exportTenantBackup = () => api.get('/api/v1/settings/backup/export', { responseType: 'blob' });
export const uploadBackup = (formData) => api.post('/api/v1/settings/backup/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
});

// Google Drive Backup
export const getGoogleAuthUrl = () => api.get('/api/v1/settings/backup/auth');
export const disconnectGoogleDrive = () => api.delete('/api/v1/settings/backup/auth'); // Delete token
export const sendGoogleAuthCode = (code) => {
    const formData = new FormData();
    formData.append('code', code);
    return api.post('/api/v1/settings/backup/callback', formData);
};
export const updateBackupSchedule = (frequency) => {
    const formData = new FormData();
    formData.append('frequency', frequency);
    return api.put('/api/v1/settings/backup/schedule', formData);
};
export const getBackupStatus = () => api.get('/api/v1/settings/backup/status');
export const triggerManualBackup = () => api.post('/api/v1/settings/backup/now');
export const purgeDeletedPatients = (tenantId) => api.delete(`/api/v1/admin/tenants/${tenantId}/purge-deleted-patients`);

// Procedures
export const getProcedures = () => api.get('/api/v1/procedures/');
export const createProcedure = (data) => api.post('/api/v1/procedures/', data);
export const updateProcedure = (id, data) => api.put(`/api/v1/procedures/${id}`, data);
export const deleteProcedure = (id) => api.delete(`/api/v1/procedures/${id}`);

// Attachments
export const uploadAttachment = (patientId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/upload/?patient_id=${patientId}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
};
export const getAttachments = (patientId) => api.get(`/patients/${patientId}/attachments`);
export const deleteAttachment = (id) => api.delete(`/api/v1/attachments/${id}`);

// Expenses
export const getExpenses = () => api.get('/api/v1/expenses/');
export const createExpense = (data) => api.post('/api/v1/expenses/', data);
export const deleteExpense = (id) => api.delete(`/api/v1/expenses/${id}`);

// Users (Admin)
export const getUsers = () => api.get('/api/v1/users/');
export const updateFcmToken = (token) => api.post('/api/v1/users/me/fcm-token', { token });
export const getDoctors = () => api.get('/api/v1/users/doctors');
export const registerUser = (data) => api.post('/api/v1/users/register/', null, { params: { username: data.username, password: data.password, role: data.role || 'doctor', permissions: data.permissions || '' } });
export const updateUser = (id, data) => api.put(`/api/v1/users/${id}`, data);
export const deleteUser = (id) => api.delete(`/api/v1/users/${id}`);

// Subscription Plans (Super Admin)
export const getSubscriptionPlans = () => api.get('/api/v1/admin/subscriptions/plans');
export const createSubscriptionPlan = (data) => api.post('/api/v1/admin/subscriptions/plans', data);
export const updateSubscriptionPlan = (id, data) => api.put(`/api/v1/admin/subscriptions/plans/${id}`, data);
export const deleteSubscriptionPlan = (id) => api.delete(`/api/v1/admin/subscriptions/plans/${id}`);

// Prescriptions
export const getPrescriptions = (patientId) => api.get(`/api/v1/patients/${patientId}/prescriptions`);
export const createPrescription = (data) => api.post('/api/v1/prescriptions/', data);
export const deletePrescription = (id) => api.delete(`/api/v1/prescriptions/${id}`);

// OCR
export const performOCR = (base64Image) => api.post('/api/v1/ocr/', { base64Image }, { timeout: 60000 });

// Laboratories
export const getLaboratories = () => api.get('/api/v1/laboratories/');
export const createLaboratory = (data) => api.post('/api/v1/laboratories/', data);
export const updateLaboratory = (id, data) => api.put(`/api/v1/laboratories/${id}`, data);
export const deleteLaboratory = (id) => api.delete(`/api/v1/laboratories/${id}`);

// Lab Orders
export const getLabOrders = (params = {}) => api.get('/api/v1/lab-orders/', { params });
export const getPatientLabOrders = (patientId) => api.get(`/api/v1/patients/${patientId}/lab_orders`);
export const createLabOrder = (data) => api.post('/api/v1/lab-orders/', data);
export const updateLabOrder = (id, data) => api.put(`/api/v1/lab-orders/${id}`, data);
export const deleteLabOrder = (id) => api.delete(`/api/v1/lab-orders/${id}`);
export const getLabOrdersStats = () => api.get('/api/v1/lab-orders/stats/summary');
export const getLabStats = (labId) => api.get(`/api/v1/laboratories/${labId}/stats`);
export const getLabPayments = (labId) => api.get(`/api/v1/laboratories/${labId}/payments`);
export const createLabPayment = (labId, data) => api.post(`/api/v1/laboratories/${labId}/payments`, data);

// Accounting
// Chart of Accounts
export const getAccounts = (type = null) => api.get(`/api/v1/accounting/accounts${type ? `?account_type=${type}` : ''}`);
export const getAccountsTree = () => api.get('/api/v1/accounting/accounts/tree');
export const createAccount = (data) => api.post('/api/v1/accounting/accounts', data);
export const updateAccount = (id, data) => api.put(`/api/v1/accounting/accounts/${id}`, data);
export const deleteAccount = (id) => api.delete(`/api/v1/accounting/accounts/${id}`);
export const getAccountBalance = (id, date = null) => api.get(`/api/v1/accounting/accounts/${id}/balance${date ? `?as_of_date=${date}` : ''}`);
export const getAccountLedger = (id, params) => api.get(`/api/v1/accounting/accounts/${id}/ledger`, { params });

// Journal Entries
export const getJournals = () => api.get('/api/v1/accounting/journals');
export const getJournalEntries = (params) => api.get('/api/v1/accounting/journal-entries', { params });
export const createJournalEntry = (data) => api.post('/api/v1/accounting/journal-entries', data);
export const getJournalEntry = (id) => api.get(`/api/v1/accounting/journal-entries/${id}`);
export const updateJournalEntry = (id, data) => api.put(`/api/v1/accounting/journal-entries/${id}`, data);
export const postJournalEntry = (id, data) => api.post(`/api/v1/accounting/journal-entries/${id}/post`, data);
export const voidJournalEntry = (id, data) => api.post(`/api/v1/accounting/journal-entries/${id}/void`, data);

// Reports
export const getTrialBalance = (date = null) => api.get(`/api/v1/accounting/reports/trial-balance${date ? `?as_of_date=${date}` : ''}`);
export const getDoctorRevenue = (start, end) => api.get('/api/v1/accounting/doctor-revenue', { params: { start_date: start, end_date: end } });
export const getDoctorDetails = (id, start, end) => api.get(`/api/v1/accounting/doctor-details/${id}`, { params: { start_date: start, end_date: end } });
export const updateStaffCompensation = (userId, commission, salary, perAppointment = 0) => api.put(`/api/v1/accounting/staff-compensation/${userId}`, null, { params: { commission_percent: commission, fixed_salary: salary, per_appointment_fee: perAppointment } });
export const getStaffRevenue = (start, end) => api.get('/api/v1/accounting/staff-revenue', { params: { start_date: start, end_date: end } });
export const getComprehensiveStats = (start, end) => api.get('/api/v1/accounting/comprehensive-stats', { params: { start_date: start, end_date: end } });

// Salary Payments
export const getSalariesStatus = (month) => api.get('/api/v1/accounting/salaries', { params: { month } });
export const recordSalaryPayment = (userId, month, amount, isPartial = false, daysWorked = null, notes = null) =>
    api.post('/api/v1/accounting/salaries', null, { params: { user_id: userId, month, amount, is_partial: isPartial, days_worked: daysWorked, notes } });
export const deleteSalaryPayment = (paymentId) => api.delete(`/api/v1/accounting/salaries/${paymentId}`);
export const updateHireDate = (userId, hireDate) => api.put(`/api/v1/accounting/staff/${userId}/hire-date`, null, { params: { hire_date: hireDate } });

// Password Reset
export const forgotPassword = (email) => api.post('/api/v1/auth/forgot-password', null, { params: { email } });
export const resetPassword = (token, newPassword) => api.post('/api/v1/auth/reset-password', null, { params: { token, new_password: newPassword } });
export const verifyResetToken = (token) => api.get('/api/v1/auth/verify-reset-token', { params: { token } });

// AI Assistant
export const sendAIQuery = (text, options = {}) => {
    const { context = null, last_patient_name = null, scribe_mode = false } = options;
    return api.post('/api/v1/ai/query', {
        text,
        context,
        last_patient_name,
        scribe_mode
    });
};
export const getAITools = () => api.get('/api/v1/ai/tools');

// AI Admin
export const getAIStats = (period = 'month') => api.get(`/api/v1/ai/admin/stats?period=${period}`);
export const getAILogs = (skip = 0, limit = 20) => api.get(`/api/v1/ai/admin/logs?skip=${skip}&limit=${limit}`);

// Notifications
export const getNotifications = () => api.get('/api/v1/notifications/');
export const markNotificationRead = (id) => api.post(`/api/v1/notifications/${id}/read`);
export const dismissNotification = (id) => api.post(`/api/v1/notifications/${id}/dismiss`);
export const broadcastNotification = (data) => api.post('/api/v1/notifications/broadcast', data);
export const deleteNotification = (id) => api.delete(`/api/v1/notifications/${id}`);

// Support & Feedback
export const submitFeedback = (data) => api.post('/api/v1/support/feedback', data);
export const getSupportMessages = () => api.get('/api/v1/support/messages');
export const updateMessageStatus = (id, status) => api.put(`/api/v1/support/messages/${id}/status?status=${status}`);
export const deleteSupportMessage = (id) => api.delete(`/api/v1/support/messages/${id}`);

// Saved Medications
export const getSavedMedications = () => api.get('/api/v1/medications/saved');
export const saveMedication = (data) => api.post('/api/v1/medications/saved', data);
export const deleteSavedMedication = (id) => api.delete(`/api/v1/medications/saved/${id}`);

// Tenant Settings (Rx Header)
export const getTenantSettings = () => api.get('/api/v1/settings/tenant');
export const updateTenantSettings = (data) => api.put('/api/v1/settings/tenant', data);


// --- Multi Price List & Insurance ---

// Price Lists
export const getPriceLists = () => api.get('/api/v1/price-lists/');
export const getDefaultPriceList = () => api.get('/api/v1/price-lists/default');
export const getPriceList = (id) => api.get(`/api/v1/price-lists/${id}`);
export const createPriceList = (data) => api.post('/api/v1/price-lists/', data);
export const updatePriceList = (id, data) => api.put(`/api/v1/price-lists/${id}`, data);
export const deactivatePriceList = (id) => api.delete(`/api/v1/price-lists/${id}`);
export const addPriceListItem = (listId, data) => api.post(`/api/v1/price-lists/${listId}/items`, data);
export const getProcedurePrices = (procedureId) => api.get(`/api/v1/price-lists/procedure/${procedureId}/prices`);

// Insurance Providers
export const getInsuranceProviders = () => api.get('/api/v1/insurance-providers/');
export const getInsuranceProvider = (id) => api.get(`/api/v1/insurance-providers/${id}`);
export const createInsuranceProvider = (data) => api.post('/api/v1/insurance-providers/', data);
export const updateInsuranceProvider = (id, data) => api.put(`/api/v1/insurance-providers/${id}`, data);
export const deactivateInsuranceProvider = (id) => api.delete(`/api/v1/insurance-providers/${id}`);
// --- Smart Session APIs ---
export const openSession = (stockItemId) => api.post('/api/v1/inventory/sessions', { stock_item_id: stockItemId });
export const closeSession = (sessionId, remaining = null) => api.post(`/api/v1/inventory/sessions/${sessionId}/close`, { actual_remaining_amount: remaining });
export const getActiveSessions = () => api.get('/api/v1/inventory/sessions/active');
