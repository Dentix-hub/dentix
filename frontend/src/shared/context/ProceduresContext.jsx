import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import logger from '@/utils/logger';
import { getProcedures } from '@/api';
import { useAuth } from '@/auth/useAuth';
const ProceduresContext = createContext(null);
export function ProceduresProvider({ children }) {
    const { user } = useAuth();
    const tenantId = user?.tenant_id;
    const [procedures, setProcedures] = useState([]);
    const [loading, setLoading] = useState(true);
    const proceduresRef = useRef([]);
    const lastFetchedRef = useRef(null);
    const cachedTenantIdRef = useRef(null);
    const activeTenantIdRef = useRef(tenantId);
    activeTenantIdRef.current = tenantId;
    const fetchProcedures = useCallback(async (force = false) => {
        // Platform users have no clinic tenant. The backend intentionally rejects
        // tenant-scoped procedure reads for them to preserve tenant isolation.
        if (tenantId == null) {
            return [];
        }

        // Cache for 5 minutes unless forced
        const CACHE_DURATION = 5 * 60 * 1000;
        if (!force
            && cachedTenantIdRef.current === tenantId
            && lastFetchedRef.current
            && Date.now() - lastFetchedRef.current < CACHE_DURATION) {
            return proceduresRef.current;
        }
        try {
            setLoading(true);
            const res = await getProcedures();
            if (activeTenantIdRef.current !== tenantId) {
                return proceduresRef.current;
            }
            const fetchedProcedures = res.data || [];
            proceduresRef.current = fetchedProcedures;
            lastFetchedRef.current = Date.now();
            cachedTenantIdRef.current = tenantId;
            setProcedures(fetchedProcedures);
            return fetchedProcedures;
        } catch (err) {
            logger.error('Failed to fetch procedures:', err);
            return proceduresRef.current; // Return cached on error
        } finally {
            if (activeTenantIdRef.current === tenantId) {
                setLoading(false);
            }
        }
    }, [tenantId]);

    useEffect(() => {
        if (tenantId == null) {
            proceduresRef.current = [];
            lastFetchedRef.current = null;
            cachedTenantIdRef.current = null;
            setProcedures([]);
            setLoading(false);
            return;
        }

        if (cachedTenantIdRef.current !== tenantId) {
            proceduresRef.current = [];
            lastFetchedRef.current = null;
            setProcedures([]);
        }
        fetchProcedures();
    }, [fetchProcedures, tenantId]);
    const value = {
        procedures,
        loading,
        refresh: () => fetchProcedures(true),
    };
    return (
        <ProceduresContext.Provider value={value}>
            {children}
        </ProceduresContext.Provider>
    );
}
export function useProcedures() {
    const context = useContext(ProceduresContext);
    if (!context) {
        throw new Error('useProcedures must be used within a ProceduresProvider');
    }
    return context;
}
export default ProceduresContext;
