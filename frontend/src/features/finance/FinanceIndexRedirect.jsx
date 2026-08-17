import { Navigate } from 'react-router-dom';
import { useFinancePermissions } from './useFinancePermissions';

/** Smart index redirect based on the user's authorized financial landing view. */
export default function FinanceIndexRedirect() {
    const { canViewOverview, isDoctor, isReceptionist } = useFinancePermissions();
    if (canViewOverview) return <Navigate to="/finance/overview" replace />;
    if (isDoctor) return <Navigate to="/finance/compensation/doctors" replace />;
    if (isReceptionist) return <Navigate to="/finance/payments" replace />;
    return <Navigate to="/finance/patient-accounts" replace />;
}
