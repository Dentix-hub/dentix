import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { useEffect, Suspense, lazy } from 'react';
import { useTranslation } from 'react-i18next';
// Auth
import AuthProvider from '@/auth/AuthProvider';
import { useAuth } from '@/auth/useAuth';
import ProtectedRoute from '@/auth/ProtectedRoute';
import { ToastProvider } from '@/shared/ui';
// Components
import LoadingSpinner from '@/shared/ui/LoadingSpinner';
import { ProceduresProvider } from '@/shared/context/ProceduresContext';
import Layout from '@/layouts/Layout';
import BackgroundWrapper from '@/shared/ui/BackgroundWrapper';
import ErrorBoundary from '@/shared/ui/ErrorBoundary';
// React Query for data caching
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '@/lib/queryClient';
// Lazy load pages
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Patients = lazy(() => import('./pages/Patients'));
const Appointments = lazy(() => import('./pages/Appointments'));
const Billing = lazy(() => import('./pages/Billing'));
const PatientDetails = lazy(() => import('./pages/PatientDetails'));
const Login = lazy(() => import('./pages/Login'));
const Settings = lazy(() => import('./pages/Settings'));
const Expenses = lazy(() => import('./pages/Expenses'));
const UsersManager = lazy(() => import('./pages/UsersManager'));
const Labs = lazy(() => import('./pages/Labs'));
const ForgotPassword = lazy(() => import('./pages/ForgotPassword'));
const ResetPassword = lazy(() => import('./pages/ResetPassword'));
const PrintInvoice = lazy(() => import('./pages/PrintInvoice'));
const PrintRx = lazy(() => import('./pages/PrintRx'));
const RegisterClinic = lazy(() => import('./pages/RegisterClinic'));
const AIStats = lazy(() => import('@/features/ai/AIStats'));
const Support = lazy(() => import('./pages/Support'));
const UserProfile = lazy(() => import('./pages/UserProfile'));
const Terms = lazy(() => import('./pages/Terms'));
const Privacy = lazy(() => import('./pages/Privacy'));
const NotFound = lazy(() => import('./pages/NotFound'));
const DentalChartPrototype = lazy(() => import('./pages/DentalChartPrototype'));
const Inventory = lazy(() => import('./pages/Inventory'));
const SmartDashboard = lazy(() => import('@/features/analytics/SmartDashboard'));
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
function AppRoutes() {
    const { isAuthenticated, loading } = useAuth();
    const { darkMode, setDarkMode, toggleDarkMode } = useUIStore();
    const { i18n } = useTranslation();
    // Sync direction with language
    useEffect(() => {
        document.documentElement.dir = i18n.language === 'ar' ? 'rtl' : 'ltr';
        document.documentElement.lang = i18n.language;
    }, [i18n.language]);
    // Initialize Theme
    useEffect(() => {
        const storedTheme = localStorage.getItem('theme');
        if (storedTheme === 'dark') {
            setDarkMode(true);
        } else {
            setDarkMode(false);
        }
    }, [setDarkMode]);
    if (loading) {
        return <LoadingSpinner />;
    }
    if (!isAuthenticated) {
        return (
            <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
                <BackgroundWrapper />
                <Suspense fallback={<LoadingSpinner />}>
                    <Routes>
                        <Route path="/register" element={<RegisterClinic isDarkMode={darkMode} />} />
                        <Route path="/forgot-password" element={<ForgotPassword />} />
                        <Route path="/reset-password" element={<ResetPassword />} />
                        <Route path="/terms" element={<Terms />} />
                        <Route path="/privacy" element={<Privacy />} />
                        <Route path="*" element={<Login isDarkMode={darkMode} toggleDarkMode={toggleDarkMode} />} />
                    </Routes>
                </Suspense>
            </Router>
        );
    }
    return (
        <ProceduresProvider>
            <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
                <BackgroundWrapper />
                <Suspense fallback={<LoadingSpinner />}>
                    <Routes>
                        {/* Print Routes (No Layout) */}
                        <Route path="/print/invoice/:id" element={<PrintInvoice />} />
                        <Route path="/print/rx/:id" element={<PrintRx />} />
                        {/* Prototype Route - Temporary */}
                        <Route path="/dental-prototype" element={<DentalChartPrototype />} />
                        {/* App Routes */}
                        <Route path="*" element={
                            <Layout>
                                <Routes>
                                    <Route path="/" element={<Dashboard />} />
                                    <Route path="/patients" element={<Patients />} />
                                    <Route path="/patients/:id" element={<PatientDetails />} />
                                    <Route path="/appointments" element={<Appointments />} />
                                    <Route path="/inventory" element={<Inventory />} />
                                    {/* Admin Protected Routes */}
                                    <Route path="/billing" element={
                                        <ProtectedRoute allowedRoles={['admin', 'super_admin']}>
                                            <Billing />
                                        </ProtectedRoute>
                                    } />
                                    <Route path="/expenses" element={
                                        <ProtectedRoute allowedRoles={['admin', 'super_admin']}>
                                            <Expenses />
                                        </ProtectedRoute>
                                    } />
                                    <Route path="/labs" element={
                                        <ProtectedRoute allowedRoles={['admin', 'super_admin']}>
                                            <Labs />
                                        </ProtectedRoute>
                                    } />
                                    <Route path="/analytics" element={
                                        <ProtectedRoute allowedRoles={['admin', 'super_admin']}>
                                            <SmartDashboard />
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
                                    {/* Super Admin Routes */}
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
                                            <AIStats />
                                        </ProtectedRoute>
                                    } />
                                    <Route path="/terms" element={<Terms />} />
                                    <Route path="/privacy" element={<Privacy />} />
                                    <Route path="/support" element={<Support />} />
                                    <Route path="/profile" element={<UserProfile />} />
                                    <Route path="*" element={<NotFound />} />
                                </Routes>
                            </Layout>
                        } />
                    </Routes>
                </Suspense>
            </Router>
        </ProceduresProvider>
    );
}
export default function App() {
    return (
        <ErrorBoundary>
            <QueryClientProvider client={queryClient}>
                <AuthProvider>
                    <ToastProvider />
                    <AppRoutes />
                </AuthProvider>
            </QueryClientProvider>
        </ErrorBoundary>
    );
}