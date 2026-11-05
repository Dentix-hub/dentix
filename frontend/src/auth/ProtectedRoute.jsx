import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './useAuth';
import { useTenantStore } from '@/store/tenant.store';

export default function ProtectedRoute({ children, allowedRoles = [], requiredFeature = null }) {
    const { user, loading, isAuthenticated } = useAuth();
    const hasFeature = useTenantStore((state) => state.hasFeature);
    const location = useLocation();

    if (loading) {
        return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
    }

    if (!isAuthenticated) {
        return <Navigate to="/" state={{ from: location }} replace />;
    }

    if (allowedRoles.length > 0 && !allowedRoles.includes(user.role)) {
        return <Navigate to="/unauthorized" replace />;
    }

    if (requiredFeature && !hasFeature(requiredFeature)) {
        return <Navigate to="/unauthorized" state={{ reason: 'feature_disabled', feature: requiredFeature }} replace />;
    }

    return children;
}
