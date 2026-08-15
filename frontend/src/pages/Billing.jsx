import { Navigate } from 'react-router-dom';

/**
 * Legacy Billing entrypoint redirecting to Finance V2 Overview (§45 MASTER_SPEC, `FIN-LEG-001`, `FIN-LEG-005`).
 */
export default function Billing() {
    return <Navigate to="/finance/overview" replace />;
}
