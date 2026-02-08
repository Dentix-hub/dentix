import React, { useState, useEffect } from 'react';
import { api, login as apiLogin, registerClinic, getMe } from '@/api';
import { getToken, setToken, removeToken, parseJwt } from '@/utils';
import AuthContext from './useAuth';
import { useTenantStore } from '@/store/tenant.store';

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
                    if (decoded) {
                        setUser({
                            username: decoded.sub,
                            role: decoded.role,
                            tenant_id: decoded.tenant_id
                        });
                    }

                    // 2. Verify with backend
                    try {
                        const res = await getMe();
                        if (res.data) {
                            setUser(prev => ({ ...prev, ...res.data }));
                            // Sync Tenant Store
                            if (res.data.tenant) {
                                useTenantStore.getState().setTenant(res.data.tenant);
                            }
                        }
                    } catch (e) {
                        console.warn("Failed to fetch full profile", e);
                    }
                } catch (err) {
                    console.error("Auth init failed", err);
                    removeToken();
                }
            }
            setLoading(false);
        };

        initAuth();
    }, []);

    const login = async (username, password, remember = true) => {
        setLoading(true);
        try {
            const res = await apiLogin(username, password);
            const { access_token, refresh_token, role } = res.data;

            setToken(access_token, refresh_token, remember);

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

    return (
        <AuthContext.Provider value={value}>
            {!loading && children}
        </AuthContext.Provider>
    );
}
