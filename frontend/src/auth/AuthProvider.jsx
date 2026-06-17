import { useEffect } from 'react';
import { login as apiLogin, registerClinic, getSessionSilent, api } from '@/api';
import { parseJwt, logout as apiLogout } from '@/utils';
import { logger } from '@/utils/logger';
import AuthContext from './useAuth';
import { useTenantStore } from '@/store/tenant.store';
import { useAuthStore } from '@/store/auth.store';

export default function AuthProvider({ children }) {
    const user = useAuthStore((state) => state.user);
    const isAuthLoading = useAuthStore((state) => state.isAuthLoading);
    const setUser = useAuthStore((state) => state.setUser);
    const setLoading = useAuthStore((state) => state.setLoading);
    const clearAuth = useAuthStore((state) => state.clearAuth);

    useEffect(() => {
        const initAuth = async () => {
            const startTime = performance.now();
            logger.log('[AUTH] Starting initialization...');

            // Safety timeout to prevent permanent loading state
            const safetyTimeout = setTimeout(() => {
                if (isAuthLoading) {
                    logger.warn('[AUTH] Initialization hanging, forcing start...');
                    setLoading(false);
                }
            }, 5000);

            try {
                logger.log('[AUTH] Validating session via cookie...');
                try {
                    const sessionRes = await getSessionSilent();
                    const userData = sessionRes.data;
                    setUser(userData);

                    // Sync Tenant Store immediately
                    await useTenantStore.getState().fetchTenant();

                    logger.log(`[AUTH] Boot successful (${Math.round(performance.now() - startTime)}ms)`);
                } catch (err) {
                    logger.error('[AUTH] Silent validation failed:', err);
                    // Cookie might be expired/invalid - user will need to login
                    clearAuth();
                }
            } catch (error) {
                logger.error('[AUTH] Init error:', error);
                clearAuth();
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

            // Check for 2FA requirement
            if (res.data.user_status === '2fa_required') {
                return res.data; // Return early, don't set user
            }

            const { user } = res.data;

            const userData = {
                id: user.id,
                username: user.name || user.email,
                role: user.role,
                tenant_id: user.tenant_id
            };
            setUser(userData);

            // Fetch tenant after login
            await useTenantStore.getState().fetchTenant();

            return res.data;
        } catch (err) {
            clearAuth();
            throw err;
        }
    };

    const verify2FA = async (code, tempToken) => {
        setLoading(true);
        try {
            const res = await api.post('/api/v1/auth/login/2fa', `code=${code}`, {
                headers: {
                    'Authorization': `Bearer ${tempToken}`,
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            });

            const { user } = res.data;

            const userData = {
                id: user.id,
                username: user.name || user.email,
                role: user.role,
                tenant_id: user.tenant_id
            };
            setUser(userData);

            await useTenantStore.getState().fetchTenant();
            return res.data;
        } catch (err) {
            clearAuth();
            throw err;
        }
    };

    const logout = async () => {
        try {
            await apiLogout();
        } catch (err) {
            logger.error('[AUTH] Logout api failed:', err);
        } finally {
            clearAuth();
        }
    };

    const register = async (data) => {
        return registerClinic(data);
    };

    const value = {
        user,
        loading: isAuthLoading,
        login,
        verify2FA,
        logout,
        register,
        isAuthenticated: !!user
    };

    // Global Splash Loading Screen
    if (isAuthLoading) {
        return (
            <div className="fixed inset-0 flex flex-col items-center justify-center bg-slate-50 dark:bg-slate-950 z-50 transition-all duration-300">
                <div className="flex flex-col items-center justify-center gap-6">
                    {/* Pulsing Branded Logo */}
                    <div className="relative">
                        <div className="absolute inset-0 rounded-full bg-primary/10 animate-ping" style={{ animationDuration: '2s' }} />
                        <div className="relative w-20 h-20 bg-gradient-to-br from-primary/15 to-primary/5 dark:from-primary/25 dark:to-primary/10 rounded-3xl flex items-center justify-center shadow-xl shadow-primary/5">
                            <svg
                                viewBox="0 0 24 24"
                                fill="none"
                                className="w-10 h-10 text-primary animate-pulse"
                                style={{ animationDuration: '1.5s' }}
                            >
                                <path
                                    d="M12 2C9.5 2 7.5 3.5 7 5.5C6.5 7.5 5 8 4 9.5C3 11 3.5 13 4.5 14.5C5.5 16 6 18 6.5 19.5C7 21 8 22 9 22C10 22 10.5 21 11 19.5C11.3 18.5 11.6 17.5 12 17.5C12.4 17.5 12.7 18.5 13 19.5C13.5 21 14 22 15 22C16 22 17 21 17.5 19.5C18 18 18.5 16 19.5 14.5C20.5 13 21 11 20 9.5C19 8 17.5 7.5 17 5.5C16.5 3.5 14.5 2 12 2Z"
                                    fill="currentColor"
                                    fillOpacity="0.2"
                                    stroke="currentColor"
                                    strokeWidth="1.5"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                />
                            </svg>
                        </div>
                    </div>
                    {/* Brand Name */}
                    <h1 className="text-2xl font-bold tracking-wider text-slate-800 dark:text-slate-100 font-sans">
                        DENTIX
                    </h1>
                    {/* Micro-animated Pulse Loading Dots */}
                    <div className="flex gap-2">
                        {[0, 1, 2].map((i) => (
                            <div
                                key={i}
                                className="w-2.5 h-2.5 rounded-full bg-primary"
                                style={{
                                    animation: 'pulse 1.2s ease-in-out infinite',
                                    animationDelay: `${i * 0.15}s`,
                                }}
                            />
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}