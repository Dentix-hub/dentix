import { Navigate, useLocation } from 'react-router-dom';
import { useFinancePermissions } from './useFinancePermissions';

function sharedPeriodSearch(search) {
    const current = new URLSearchParams(search);
    const next = new URLSearchParams();
    ['from', 'to', 'preset'].forEach((key) => {
        const value = current.get(key);
        if (value) next.set(key, value);
    });
    return next.toString();
}

/** Smart index redirect based on the user's authorized Finance destination. */
export default function FinanceIndexRedirect() {
    const location = useLocation();
    const {
        canViewOverview,
        canViewPatientAccounts,
        canViewPayments,
        canViewExpenses,
        canViewActivity,
        isDoctor,
    } = useFinancePermissions();

    let pathname = '/finance/patient-accounts';
    if (canViewOverview) pathname = '/finance/overview';
    else if (isDoctor) pathname = '/finance/team/doctors';
    else if (canViewPayments) pathname = '/finance/cash-movements/payments';
    else if (canViewExpenses || canViewActivity) pathname = '/finance/cash-movements';
    else if (canViewPatientAccounts) pathname = '/finance/patient-accounts';

    const periodSearch = sharedPeriodSearch(location.search);
    return (
        <Navigate
            replace
            to={{
                pathname,
                search: periodSearch ? `?${periodSearch}` : '',
            }}
        />
    );
}
