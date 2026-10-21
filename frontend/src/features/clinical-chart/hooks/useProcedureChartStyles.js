import { useCallback, useContext, useEffect, useState } from 'react';
import { QueryClientContext } from '@tanstack/react-query';
import {
    deleteProcedureChartStyle,
    getProcedureChartStyles,
    upsertProcedureChartStyle,
} from '@/api/procedures';
import { invalidatePatientClinicalQueries } from '@/features/patients/utils/invalidatePatientClinicalQueries';
import { useProcedures } from '@/shared/context/ProceduresContext';

export const PROCEDURE_CHART_STYLES_QUERY_KEY = ['procedure-chart-styles'];

/**
 * Hook for reading, upserting, and deleting procedure chart appearance styles
 * (`/api/v1/procedure-chart-styles`), invalidating both the procedures catalog
 * and patient clinical workspace queries on change (U4C #1).
 */
export function useProcedureChartStyles({ patientId = null, enabled = true } = {}) {
    const queryClient = useContext(QueryClientContext) || null;
    const procCtx = useProcedures();
    const refreshProcedures = procCtx?.refresh || null;

    const [styles, setStyles] = useState([]);
    const [loading, setLoading] = useState(Boolean(enabled));
    const [savingByName, setSavingByName] = useState({});

    const invalidateAllRelated = useCallback(async () => {
        if (refreshProcedures) {
            await refreshProcedures();
        }
        if (queryClient) {
            queryClient.invalidateQueries({ queryKey: PROCEDURE_CHART_STYLES_QUERY_KEY });
            queryClient.invalidateQueries({ queryKey: ['procedures'] });
            invalidatePatientClinicalQueries(queryClient, patientId);
        }
    }, [patientId, queryClient, refreshProcedures]);

    const fetchStyles = useCallback(async () => {
        if (!enabled) return [];
        try {
            setLoading(true);
            const res = await getProcedureChartStyles();
            const list = Array.isArray(res?.data) ? res.data : (Array.isArray(res) ? res : []);
            setStyles(list);
            return list;
        } catch {
            return [];
        } finally {
            setLoading(false);
        }
    }, [enabled]);

    useEffect(() => {
        if (enabled) {
            void fetchStyles();
        }
    }, [enabled, fetchStyles]);

    const saveStyle = useCallback(async ({ procedure_name, template, color_key = null }) => {
        const cleanName = String(procedure_name || '').trim();
        const normalizedColorKey = template === 'NONE' ? null : (color_key || null);
        setSavingByName((prev) => ({ ...prev, [cleanName]: true }));
        try {
            const res = await upsertProcedureChartStyle({
                procedure_name: cleanName,
                template,
                color_key: normalizedColorKey,
            });
            const saved = res?.data ?? res;
            setStyles((prev) => {
                const filtered = prev.filter((item) => item.procedure_name !== cleanName);
                return saved && typeof saved === 'object' ? [...filtered, saved] : filtered;
            });
            await invalidateAllRelated();
            return saved;
        } finally {
            setSavingByName((prev) => ({ ...prev, [cleanName]: false }));
        }
    }, [invalidateAllRelated]);

    const clearStyle = useCallback(async ({ id, procedure_name }) => {
        const cleanName = String(procedure_name || '').trim();
        let styleId = id;
        if (styleId == null && cleanName) {
            const existing = styles.find((s) => s.procedure_name === cleanName);
            styleId = existing?.id;
            if (styleId == null) {
                const latest = await fetchStyles();
                styleId = latest.find((s) => s.procedure_name === cleanName)?.id;
            }
        }
        if (styleId == null) {
            await invalidateAllRelated();
            return false;
        }
        setSavingByName((prev) => ({ ...prev, [cleanName]: true }));
        try {
            await deleteProcedureChartStyle(styleId);
            setStyles((prev) => prev.filter((item) => item.id !== styleId && item.procedure_name !== cleanName));
            await invalidateAllRelated();
            return true;
        } finally {
            setSavingByName((prev) => ({ ...prev, [cleanName]: false }));
        }
    }, [fetchStyles, invalidateAllRelated, styles]);

    return {
        styles,
        loading,
        savingByName,
        refreshStyles: fetchStyles,
        saveStyle,
        clearStyle,
    };
}

export default useProcedureChartStyles;
