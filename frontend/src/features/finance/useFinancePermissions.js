import { useMemo } from 'react';
import { useAuth } from '@/auth/useAuth';

/**
 * Hook for role-based financial permissions and visibility rules (§4 MASTER_SPEC, GEMINI_REPAIR_PLAN R4).
 * Mirrors backend authorization contracts (Permission.FINANCIAL_READ, FINANCIAL_WRITE, SYSTEM_CONFIG).
 */
export function useFinancePermissions() {
    const { user } = useAuth();

    return useMemo(() => {
        const role = (user?.role || '').toLowerCase();
        const isAdmin = role === 'admin' || role === 'super_admin';
        const isSuperAdmin = role === 'super_admin';
        const isManager = role === 'manager';
        const isAccountant = role === 'accountant';
        const isDoctor = role === 'doctor';
        const isReceptionist = role === 'receptionist';
        const isStaff = isReceptionist || role === 'assistant' || role === 'nurse';

        // Parse custom permissions list if present
        let permissionsList = [];
        if (user?.permissions) {
            try {
                permissionsList = typeof user.permissions === 'string'
                    ? JSON.parse(user.permissions)
                    : user.permissions;
                if (!Array.isArray(permissionsList)) permissionsList = [];
            } catch {
                permissionsList = [];
            }
        }

        const hasPermission = (perm) => {
            if (isAdmin) return true;
            return permissionsList.includes(perm);
        };

        // Canonical backend permissions with colon support
        const canReadFinance = isAdmin || isManager || isAccountant || hasPermission('financial:read') || hasPermission('financial_read') || hasPermission('FINANCIAL_READ');
        const canWriteFinance = isAdmin || isManager || isAccountant || isReceptionist || hasPermission('financial:write') || hasPermission('financial_write') || hasPermission('FINANCIAL_WRITE');
        const canConfigFinance = isAdmin || isManager || hasPermission('system:config') || hasPermission('system_config') || hasPermission('SYSTEM_CONFIG');

        // Route & Feature visibility
        const canViewOverview = isAdmin || isManager || isAccountant;
        const canViewExpenses = isAdmin || isManager || isAccountant;
        const canViewReports = isAdmin || isManager || isAccountant;
        const canViewPayroll = isAdmin || isManager || isAccountant;
        const canViewActivity = isAdmin || isManager || isAccountant || isReceptionist;
        const canViewPayments = isAdmin || isManager || isAccountant || isReceptionist;
        const canViewPatientAccounts = isAdmin || isManager || isAccountant || isReceptionist;

        const canViewAllDoctors = isAdmin || isManager || isAccountant;
        const canViewDoctorCompensation = (doctorId) => {
            if (isAdmin || isManager || isAccountant) return true;
            if (isDoctor && user?.id === Number(doctorId)) return true;
            return false;
        };

        const canManageSalaries = isAdmin || isManager || (canWriteFinance && canConfigFinance);
        const canDeleteFinancialRecord = isAdmin || isManager || (canWriteFinance && canConfigFinance);
        const canExportReports = isAdmin || isManager || isAccountant;

        const hasCrossDoctorPatientHistory = Boolean(user?.can_view_other_doctors_history);

        return {
            user,
            role,
            isAdmin,
            isSuperAdmin,
            isManager,
            isAccountant,
            isDoctor,
            isReceptionist,
            isStaff,
            hasPermission,
            canReadFinance,
            canWriteFinance,
            canConfigFinance,
            canViewOverview,
            canViewExpenses,
            canViewReports,
            canViewPayroll,
            canViewActivity,
            canViewPayments,
            canViewPatientAccounts,
            canViewAllDoctors,
            canViewDoctorCompensation,
            canManageSalaries,
            canDeleteFinancialRecord,
            canExportReports,
            hasCrossDoctorPatientHistory,
        };
    }, [user]);
}
