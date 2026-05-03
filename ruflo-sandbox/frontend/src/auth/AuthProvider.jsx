import { useState, useEffect } from 'react';
import { login as apiLogin, registerClinic, getMeSilent } from '@/api';
import { getToken, setToken, removeToken, parseJwt } from '@/utils';
import AuthContext from './useAuth';
import { useTenantStore } from '@/store/tenant.store';
import LoadingSpinner from '@/shared/ui/LoadingSpinner';
export default function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    useEffect(() => {
        const initAuth = async () => {
            const token = getToken();
            if (token) {
                try {
                    // 1. Decode locally for fast UI
                    const decoded = parseJwt(token);
                    if (!decoded) {
                        removeToken();
                        setLoading(false);
                        return;
                    }
                    // 1b. Check if token is expired before hitting backend
                    const now = Date.now() / 1000;
                    if (decoded.exp && decoded.exp < now) {
                        console.warn('Token expired, clearing session');
                        removeToken();
                        setLoading(false);
                        return;
                    }
                    setUser({
                        username: decoded.sub,
                        role: decoded.role,
                        tenant_id: decoded.tenant_id
                    });
                    // 2. Verify with backend (silent — won't trigger interceptor redirect)
                    try {
                        const res = await getMeSilent();
                        if (res.data) {
                            setUser(prev => ({ ...prev, ...res.data }));
                            // Sync Tenant Store
                            if (res.data.tenant) {
                                useTenantStore.getState().setTenant(res.data.tenant);
                            }
                        }
                    } catch (e) {
                        // If backend says 401, token is invalid — clean up quietly
                        if (e.response?.status === 401) {
                            console.warn('Session expired, clearing token');
                            removeToken();
                            setUser(null);
                        } else {
                            // Network error or other issue — keep local session alive
                            console.warn('Failed to fetch profile, keeping local session', e);
                        }
                    }
                } catch (err) {
                    console.error('Auth init failed', err);
                    removeToken();
                }
            }
            setLoading(false);
        };
        initAuth();
    }, []);
    const login = async (username, password) => {
        setLoading(true);
        try {
            const res = await apiLogin(username, password);
            const { access_token, refresh_token, role } = res.data;
            setToken(access_token, refresh_token);
            // Decoded User
            const decoded = parseJwt(access_token);
            setUser({
                username: decoded.sub,
                role: role,
                tenant_id: decoded.tenant_id
            });
            return res.data;
        } catch (err) {
            throw err;
        } finally {
            setLoading(false);
        }
    };
    const logout = () => {
        removeToken();
        setUser(null);
        window.location.href = '/';
    };
    const register = async (data) => {
        return registerClinic(data);
    };
    const value = {
        user,
        loading,
        login,
        logout,
        register,
        isAuthenticated: !!user
    };
    if (loading) {
        return <LoadingSpinner />;
    }
    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}

