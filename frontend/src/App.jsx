import { Routes, Route, useLocation } from 'react-router-dom';
import logger from '@/utils/logger';
import { useEffect, Suspense, lazy } from 'react';
import { useTranslation } from 'react-i18next';
// Auth
import AuthProvider from '@/auth/AuthProvider';
import { useAuth } from '@/auth/useAuth';
import ProtectedRoute from '@/auth/ProtectedRoute';
import ToastProvider from '@/shared/ui/ToastProvider';
// Components
import LoadingSpinner from '@/shared/ui/LoadingSpinner';
import { ProceduresProvider } from '@/shared/context/ProceduresContext';
const Layout = lazy(() => import('@/layouts/Layout'));
import BackgroundWrapper from '@/shared/ui/BackgroundWrapper';
import RootErrorBoundary from '@/shared/ui/ErrorBoundary';
import GlobalErrorFallback from '@/shared/ui/GlobalErrorFallback';
// React Query for data caching
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '@/lib/queryClient';
import { MotionProvider } from '@/lib/motion';
// Lazy load pages
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Patients = lazy(() => import('./pages/Patients'));
const Appointments = lazy(() => import('./pages/Appointments'));
const PatientDetails = lazy(() => import('./pages/PatientDetails'));
const Login = lazy(() => import('./pages/Login'));
const Settings = lazy(() => import('./pages/Settings'));
const UsersManager = lazy(() => import('./pages/UsersManager'));
const Labs = lazy(() => import('./pages/Labs'));
const ForgotPassword = lazy(() => import('./pages/ForgotPassword'));
const ResetPassword = lazy(() => import('./pages/ResetPassword'));
const PrintInvoice = lazy(() => import('./pages/PrintInvoice'));
const PrintRx = lazy(() => import('./pages/PrintRx'));
const RegisterClinic = lazy(() => import('./pages/RegisterClinic'));
const AIStatsPage = lazy(() => import('./pages/admin/AIStatsPage'));
const Support = lazy(() => import('./pages/Support'));
const UserProfile = lazy(() => import('./pages/UserProfile'));
const Terms = lazy(() => import('./pages/Terms'));
const Privacy = lazy(() => import('./pages/Privacy'));
const NotFound = lazy(() => import('./pages/NotFound'));
const Inventory = lazy(() => import('./pages/Inventory'));
// Finance V2 Pages
const FinanceLayout = lazy(() => import('@/features/finance/FinanceLayout'));
import FinanceIndexRedirect from '@/features/finance/FinanceIndexRedirect';
import LegacyFinanceRedirect from '@/features/finance/LegacyFinanceRedirect';
const OverviewPage = lazy(() => import('@/features/finance/pages/OverviewPage'));
const PatientAccountsPage = lazy(() => import('@/features/finance/pages/PatientAccountsPage'));
const CashMovementsLayout = lazy(() => import('@/features/finance/pages/CashMovementsLayout'));
const PaymentsPage = lazy(() => import('@/features/finance/pages/PaymentsPage'));
const ExpensesPage = lazy(() => import('@/features/finance/pages/ExpensesPage'));
const ActivityPage = lazy(() => import('@/features/finance/pages/ActivityPage'));
const TeamLayout = lazy(() => import('@/features/finance/pages/TeamLayout'));
const DoctorsPage = lazy(() => import('@/features/finance/pages/DoctorsPage'));
const DoctorDetailPage = lazy(() => import('@/features/finance/pages/DoctorDetailPage'));
const PayrollPage = lazy(() => import('@/features/finance/pages/PayrollPage'));
const ReportsPage = lazy(() => import('@/features/finance/pages/ReportsPage'));
// New Admin Pages
const AdminOverview = lazy(() => import('./pages/admin/Overview'));
const AdminTenants = lazy(() => import('./pages/admin/TenantsPage'));
const AdminUsers = lazy(() => import('./pages/admin/UsersPage'));
const AdminFinance = lazy(() => import('./pages/admin/FinancePage'));
const AdminComms = lazy(() => import('./pages/admin/CommunicationsPage'));
const AdminSystem = lazy(() => import('./pages/admin/SystemPage'));
const SystemLogs = lazy(() => import('./pages/admin/SystemLogs'));
const PriceLists = lazy(() => import('./pages/admin/PriceLists'));
const InsuranceProviders = lazy(() => import('./pages/admin/InsuranceProviders'));
// Stores
import { useUIStore } from '@/store/ui.store';
import ImpersonationBar from '@/components/common/ImpersonationBar';
import { InstallPrompt } from '@/components/InstallPrompt';

function AppRoutes() {
    const { isAuthenticated, isBooting } = useAuth();
    const location = useLocation();
    const { darkMode, setDarkMode, toggleDarkMode } = useUIStore();
    const { i18n } = useTranslation();

    useEffect(() => {
        logger.log(`[DENTIX] Build ID: 20260508-1447`);
    }, []);

    useEffect(() => {
        if (!isBooting) {
            logger.log(`[ROUTER] Navigation detected: ${location.pathname} (Authenticated: ${isAuthenticated})`);
        }
    }, [location.pathname, isAuthenticated, isBooting]);

    useEffect(() => {
        document.documentElement.dir = i18n.language === 'ar' ? 'rtl' : 'ltr';
        document.documentElement.lang = i18n.language;
    }, [i18n.language]);

    useEffect(() => {
        const storedTheme = localStorage.getItem('theme');
        if (storedTheme === 'dark') {
            setDarkMode(true);
        } else {
            setDarkMode(false);
        }
    }, [setDarkMode]);

    if (isBooting) {
        return <LoadingSpinner />;
    }

    if (!isAuthenticated) {
        return (
            <>
                <ImpersonationBar />
                <BackgroundWrapper />
                <Suspense fallback={<LoadingSpinner />}>
                    <Routes>
                        <Route path="/" element={<Login isDarkMode={darkMode} toggleDarkMode={toggleDarkMode} />} />
                        <Route path="/login" element={<Login isDarkMode={darkMode} toggleDarkMode={toggleDarkMode} />} />
                        <Route path="/register" element={<RegisterClinic isDarkMode={darkMode} />} />
                        <Route path="/forgot-password" element={<ForgotPassword />} />
                        <Route path="/reset-password" element={<ResetPassword />} />
                        <Route path="/terms" element={<Terms />} />
                        <Route path="/privacy" element={<Privacy />} />
                        <Route path="*" element={<Login isDarkMode={darkMode} toggleDarkMode={toggleDarkMode} />} />
                    </Routes>
                </Suspense>
            </>
        );
    }

    return (
        <ProceduresProvider>
            <>
                <ImpersonationBar />
                <BackgroundWrapper />
                <Suspense fallback={<LoadingSpinner />}>
                    <Routes>
                        <Route path="/print/invoice/:id" element={<PrintInvoice />} />
                        <Route path="/print/rx/:id" element={<PrintRx />} />
                        <Route element={
                            <RootErrorBoundary fallback={<GlobalErrorFallback />}>
                                <Layout />
                            </RootErrorBoundary>
                        }>
                            <Route path="/" element={<Dashboard />} />
                            <Route path="/patients" element={<Patients />} />
                            <Route path="/patients/:id" element={<PatientDetails />} />
                            <Route path="/appointments" element={<Appointments />} />
                            <Route path="/inventory" element={<Inventory />} />

                            {/* Legacy top-level Finance links remain compatibility-only. */}
                            <Route path="/billing" element={<LegacyFinanceRedirect to="/finance/overview" />} />
                            <Route path="/billing/*" element={<LegacyFinanceRedirect to="/finance/overview" />} />
                            <Route path="/expenses" element={<LegacyFinanceRedirect to="/finance/cash-movements/expenses" />} />
                            <Route path="/expenses/*" element={<LegacyFinanceRedirect to="/finance/cash-movements/expenses" />} />

                            <Route
                                path="/finance"
                                element={
                                    <ProtectedRoute allowedRoles={['admin', 'super_admin', 'manager', 'accountant', 'receptionist', 'doctor']}>
                                        <FinanceLayout />
                                    </ProtectedRoute>
                                }
                            >
                                <Route index element={<FinanceIndexRedirect />} />
                                <Route path="overview" element={<OverviewPage />} />
                                <Route path="patient-accounts" element={<PatientAccountsPage />} />
                                <Route path="patient-accounts/:patientId" element={<PatientAccountsPage />} />

                                <Route path="cash-movements" element={<CashMovementsLayout />}>
                                    <Route path="payments" element={<PaymentsPage />} />
                                    <Route path="expenses" element={<ExpensesPage />} />
                                    <Route path="activity" element={<ActivityPage />} />
                                </Route>

                                <Route path="team" element={<TeamLayout />}>
                                    <Route path="doctors" element={<DoctorsPage />} />
                                    <Route path="doctors/:doctorId" element={<DoctorDetailPage />} />
                                    <Route path="payroll" element={<PayrollPage />} />
                                </Route>

                                <Route path="reports" element={<ReportsPage />} />

                                {/* PR5 compatibility routes: bookmarks normalize without duplicating screens. */}
                                <Route path="payments" element={<LegacyFinanceRedirect to="/finance/cash-movements/payments" />} />
                                <Route path="expenses" element={<LegacyFinanceRedirect to="/finance/cash-movements/expenses" />} />
                                <Route path="activity" element={<LegacyFinanceRedirect to="/finance/cash-movements/activity" />} />
                                <Route path="compensation" element={<LegacyFinanceRedirect to="/finance/team" />} />
                                <Route path="compensation/doctors" element={<LegacyFinanceRedirect to="/finance/team/doctors" />} />
                                <Route
                                    path="compensation/doctors/:doctorId"
                                    element={<LegacyFinanceRedirect to={({ doctorId }) => `/finance/team/doctors/${doctorId}`} />}
                                />
                                <Route path="compensation/payroll" element={<LegacyFinanceRedirect to="/finance/team/payroll" />} />
                            </Route>

                            <Route path="/labs" element={
                                <ProtectedRoute allowedRoles={['admin', 'super_admin']}>
                                    <Labs />
                                </ProtectedRoute>
                            } />
                            <Route path="/analytics" element={
                                <ProtectedRoute allowedRoles={['admin', 'super_admin']}>
                                    <LegacyFinanceRedirect to="/finance/reports" />
                                </ProtectedRoute>
                            } />
                            <Route path="/analytics/*" element={
                                <ProtectedRoute allowedRoles={['admin', 'super_admin']}>
                                    <LegacyFinanceRedirect to="/finance/reports" />
                                </ProtectedRoute>
                            } />
                            <Route path="/users" element={
                                <ProtectedRoute allowedRoles={['admin', 'super_admin']}>
                                    <UsersManager />
                                </ProtectedRoute>
                            } />
                            <Route path="/settings" element={
                                <ProtectedRoute allowedRoles={['admin', 'super_admin']}>
                                    <Settings />
                                </ProtectedRoute>
                            } />
                            <Route path="/settings/price-lists" element={
                                <ProtectedRoute allowedRoles={['admin', 'super_admin']}>
                                    <PriceLists />
                                </ProtectedRoute>
                            } />
                            <Route path="/settings/insurance" element={
                                <ProtectedRoute allowedRoles={['admin', 'super_admin']}>
                                    <InsuranceProviders />
                                </ProtectedRoute>
                            } />
                            <Route path="/admin" element={
                                <ProtectedRoute allowedRoles={['super_admin']}>
                                    <AdminOverview />
                                </ProtectedRoute>
                            } />
                            <Route path="/admin/tenants" element={
                                <ProtectedRoute allowedRoles={['super_admin']}>
                                    <AdminTenants />
                                </ProtectedRoute>
                            } />
                            <Route path="/admin/users" element={
                                <ProtectedRoute allowedRoles={['super_admin']}>
                                    <AdminUsers />
                                </ProtectedRoute>
                            } />
                            <Route path="/admin/finance" element={
                                <ProtectedRoute allowedRoles={['super_admin']}>
                                    <AdminFinance />
                                </ProtectedRoute>
                            } />
                            <Route path="/admin/messages" element={
                                <ProtectedRoute allowedRoles={['super_admin']}>
                                    <AdminComms />
                                </ProtectedRoute>
                            } />
                            <Route path="/admin/settings" element={
                                <ProtectedRoute allowedRoles={['super_admin']}>
                                    <AdminSystem />
                                </ProtectedRoute>
                            } />
                            <Route path="/admin/system/logs" element={
                                <ProtectedRoute allowedRoles={['super_admin']}>
                                    <SystemLogs />
                                </ProtectedRoute>
                            } />
                            <Route path="/ai/stats" element={
                                <ProtectedRoute allowedRoles={['super_admin']}>
                                    <AIStatsPage />
                                </ProtectedRoute>
                            } />
                            <Route path="/terms" element={<Terms />} />
                            <Route path="/privacy" element={<Privacy />} />
                            <Route path="/support" element={<Support />} />
                            <Route path="/profile" element={<UserProfile />} />
                            <Route path="*" element={<NotFound />} />
                        </Route>
                    </Routes>
                </Suspense>
            </>
        </ProceduresProvider>
    );
}

export default function App() {
    return (
        <RootErrorBoundary>
            <QueryClientProvider client={queryClient}>
                <AuthProvider>
                    <MotionProvider>
                        <ToastProvider />
                        <AppRoutes />
                        <InstallPrompt />
                    </MotionProvider>
                </AuthProvider>
            </QueryClientProvider>
        </RootErrorBoundary>
    );
}
