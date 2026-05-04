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
            const startTime = performance.now();
            console.log('[AUTH] Starting initialization...');

            // Safety timeout to prevent permanent loading state
            const safetyTimeout = setTimeout(() => {
                if (loading) {
                    console.warn('[AUTH] Initialization hanging, forcing start...');
                    setLoading(false);
                }
            }, 5000);

            try {
                const token = getToken();
                if (token) {
                    console.log('[AUTH] Token found, validating...');
                    try {
                        const userRes = await getMeSilent();
                        setUser(userRes.data);
                        
                        // Sync Tenant Store immediately
                        if (userRes.data.tenant) {
                            useTenantStore.getState().setTenant(userRes.data.tenant);
                        } else {
                            await useTenantStore.getState().fetchTenant();
                        }
                        
                        console.log(`[AUTH] Boot successful (${Math.round(performance.now() - startTime)}ms)`);
                    } catch (err) {
                        console.error('[AUTH] Silent validation failed:', err);
                        removeToken();
                        setUser(null);
                    }
                } else {
                    console.log('[AUTH] No token found.');
                }
            } catch (error) {
                console.error('[AUTH] Init error:', error);
            } finally {
                clearTimeout(safetyTimeout);
                setLoading(false);
            }
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
            
            // Fetch tenant after login
            await useTenantStore.getState().fetchTenant();
            
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
