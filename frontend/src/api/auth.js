import { api } from './apiClient';

export const login = (username, password) => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    return api.post('/api/v1/auth/token', formData);
};

export const registerClinic = (data) => api.post('/api/v1/auth/register_clinic', data);
export const getMe = () => api.get('/api/v1/users/me');
// Silent variant: 401 won't trigger interceptor redirect (used during auth init)
export const getMeSilent = () => api.get('/api/v1/users/me', { _silentAuth: true });
export const updateProfile = (data) => api.put('/api/v1/users/me', data);
export const forgotPassword = (email) => api.post('/api/v1/auth/forgot-password', null, { params: { email } });
export const resetPassword = (token, newPassword) => api.post('/api/v1/auth/reset-password', null, { params: { token, new_password: newPassword } });
export const verifyResetToken = (token) => api.get('/api/v1/auth/verify-reset-token', { params: { token } });
