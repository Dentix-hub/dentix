import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import ProtectedRoute from '@/auth/ProtectedRoute';
import SubscriptionBanner from '@/shared/ui/SubscriptionBanner';
import { useTenantStore } from '@/store/tenant.store';
import AuthContext from '@/auth/useAuth';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Mock translation
vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, optionsOrDef) => {
            if (typeof optionsOrDef === 'string') return optionsOrDef;
            if (optionsOrDef?.defaultValue) return optionsOrDef.defaultValue;
            return key;
        },
        i18n: { language: 'ar' },
    }),
}));

describe('PR-10 Commercial Frontend Consistency & Gating', () => {
    beforeEach(() => {
        useTenantStore.getState().clearTenant();
    });

    describe('ProtectedRoute capability and role enforcement', () => {
        function renderRoute(authValue, ui) {
            return render(
                <MemoryRouter initialEntries={['/guarded']}>
                    <AuthContext.Provider value={authValue}>
                        <Routes>
                            <Route path="/" element={<div>Root Login</div>} />
                            <Route path="/guarded" element={ui} />
                            <Route path="/unauthorized" element={<div>Access Denied</div>} />
                        </Routes>
                    </AuthContext.Provider>
                </MemoryRouter>
            );
        }

        it('redirects to /unauthorized when requiredFeature is not in tenant capabilities', () => {
            useTenantStore.setState({
                features: { LABORATORIES: false },
            });

            renderRoute(
                { user: { role: 'admin' }, loading: false, isAuthenticated: true },
                <ProtectedRoute requiredFeature="LABORATORIES">
                    <div>Laboratory Orders Desk</div>
                </ProtectedRoute>
            );

            expect(screen.getByText('Access Denied')).toBeInTheDocument();
            expect(screen.queryByText('Laboratory Orders Desk')).not.toBeInTheDocument();
        });

        it('grants access when requiredFeature is true in tenant capabilities', () => {
            useTenantStore.setState({
                features: { LABORATORIES: true },
            });

            renderRoute(
                { user: { role: 'admin' }, loading: false, isAuthenticated: true },
                <ProtectedRoute requiredFeature="LABORATORIES">
                    <div>Laboratory Orders Desk</div>
                </ProtectedRoute>
            );

            expect(screen.getByText('Laboratory Orders Desk')).toBeInTheDocument();
            expect(screen.queryByText('Access Denied')).not.toBeInTheDocument();
        });

        it('denies user when role does not match even if feature is active', () => {
            useTenantStore.setState({
                features: { LABORATORIES: true },
            });

            renderRoute(
                { user: { role: 'receptionist' }, loading: false, isAuthenticated: true },
                <ProtectedRoute allowedRoles={['admin', 'super_admin']} requiredFeature="LABORATORIES">
                    <div>Laboratory Orders Desk</div>
                </ProtectedRoute>
            );

            expect(screen.getByText('Access Denied')).toBeInTheDocument();
            expect(screen.queryByText('Laboratory Orders Desk')).not.toBeInTheDocument();
        });
    });

    describe('SubscriptionBanner truthful server status rendering', () => {
        function renderBanner(role = 'admin') {
            return render(
                <MemoryRouter>
                    <AuthContext.Provider value={{ user: { role }, loading: false, isAuthenticated: true }}>
                        <SubscriptionBanner />
                    </AuthContext.Provider>
                </MemoryRouter>
            );
        }

        it('renders read-only notice when subscription is EXPIRED', () => {
            useTenantStore.setState({
                entitlements: {
                    effective_subscription_status: 'EXPIRED',
                    is_past_end: true,
                    is_in_grace: false,
                    can_write_clinical: false,
                    can_write_billable: false,
                },
            });

            renderBanner();
            expect(screen.getByText(/وضع القراءة فقط مفعل/i)).toBeInTheDocument();
        });

        it('renders grace period warning when status is GRACE', () => {
            const graceUntil = new Date(Date.now() + 5 * 24 * 60 * 60 * 1000).toISOString();
            useTenantStore.setState({
                entitlements: {
                    effective_subscription_status: 'GRACE',
                    is_past_end: true,
                    is_in_grace: true,
                    grace_period_until: graceUntil,
                },
            });

            renderBanner();
            expect(screen.getByText(/فترة السماح سارية/i)).toBeInTheDocument();
        });

        it('renders commercial suspension notice when status is SUSPENDED', () => {
            useTenantStore.setState({
                entitlements: {
                    effective_subscription_status: 'SUSPENDED',
                    is_past_end: false,
                    is_in_grace: false,
                },
            });

            renderBanner();
            expect(screen.getByText(/تم تعليق الاشتراك تجارياً/i)).toBeInTheDocument();
        });

        it('renders security disabled notice when status is HARD_DISABLED', () => {
            useTenantStore.setState({
                entitlements: {
                    effective_subscription_status: 'HARD_DISABLED',
                    is_hard_disabled: true,
                },
            });

            renderBanner();
            expect(screen.getByText(/تم تعطيل الحساب لأسباب أمنية/i)).toBeInTheDocument();
        });

        it('never renders commercial banner for super_admin impersonation', () => {
            useTenantStore.setState({
                entitlements: {
                    effective_subscription_status: 'EXPIRED',
                    is_past_end: true,
                    is_in_grace: false,
                },
            });

            renderBanner('super_admin');
            expect(screen.queryByText(/وضع القراءة فقط/i)).not.toBeInTheDocument();
        });
    });

    describe('Stale session & tenant switch clearance', () => {
        it('clearTenant purges cached decisions preventing cross-tenant leakage', () => {
            useTenantStore.setState({
                tenant: { id: 101, name: 'Clinic A', plan: 'enterprise' },
                entitlements: { effective_subscription_status: 'ACTIVE' },
                features: { BILLING: true, INVENTORY: true, LABORATORIES: true },
            });

            expect(useTenantStore.getState().hasFeature('BILLING')).toBe(true);

            // Trigger tenant logout / switch
            useTenantStore.getState().clearTenant();

            const clearedState = useTenantStore.getState();
            expect(clearedState.tenant).toBeNull();
            expect(clearedState.entitlements).toBeNull();
            expect(clearedState.features).toEqual({});
            expect(clearedState.hasFeature('BILLING')).toBe(false);
            expect(clearedState.hasFeature('INVENTORY')).toBe(false);
        });
    });

    describe('Flutter freeze policy compliance', () => {
        it('documents Flutter client freeze policy and excludes unsupported mobile commercial claims', () => {
            const policyPath = path.resolve(__dirname, '../../../docs/flutter-freeze-policy.md');
            expect(fs.existsSync(policyPath)).toBe(true);

            const content = fs.readFileSync(policyPath, 'utf-8');
            expect(content).toContain('frozen as a feature surface');
            expect(content).toContain('The React/Vite PWA is the primary mobile client');
        });
    });
});
