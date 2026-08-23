import { useQuery } from '@tanstack/react-query';
import { getPatientReportDetails, getPatientsReport } from '@/api/financials';
import { financeKeys } from '../../queryKeys';

const unwrap = (res) => res?.data?.data ?? res?.data ?? null;

/**
 * Resolve one patient's period statement plus the all-time account balance.
 * Both requests use RECEIVABLE_READ endpoints so collection-only roles do not
 * need REPORT_READ just to follow a patient-account deep link.
 */
export function usePatientStatement(patientId, { from, to } = {}) {
    const normalizedId = Number(patientId);
    const enabled = Number.isInteger(normalizedId) && normalizedId > 0;

    const statementQuery = useQuery({
        queryKey: financeKeys.patientStatement(normalizedId, { from: from || '', to: to || '' }),
        queryFn: async () => {
            const params = {};
            if (from && to) {
                params.start_date = from;
                params.end_date = to;
            }
            const res = await getPatientReportDetails(normalizedId, params);
            return unwrap(res);
        },
        enabled,
        staleTime: 30 * 1000,
    });

    const accountQuery = useQuery({
        queryKey: financeKeys.patientAccount(normalizedId, { scope: 'all_time' }),
        queryFn: async () => {
            const res = await getPatientsReport({
                patient_id: normalizedId,
                skip: 0,
                limit: 1,
            });
            const data = unwrap(res) || {};
            return Array.isArray(data.patients) ? data.patients[0] || null : null;
        },
        enabled,
        staleTime: 30 * 1000,
    });

    const statement = statementQuery.data;
    const account = accountQuery.data;
    const data = statement
        ? {
            ...account,
            ...statement,
            all_time_outstanding: Number(account?.all_time_outstanding ?? 0),
        }
        : account;

    return {
        data,
        isLoading: enabled && (statementQuery.isLoading || accountQuery.isLoading),
        isError: !enabled || statementQuery.isError || accountQuery.isError,
        refetch: async () => Promise.all([
            statementQuery.refetch(),
            accountQuery.refetch(),
        ]),
    };
}
