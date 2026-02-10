import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getProcedures } from '@/api';
const ProceduresContext = createContext(null);
export function ProceduresProvider({ children }) {
    const [procedures, setProcedures] = useState([]);
    const [loading, setLoading] = useState(true);
    const [lastFetched, setLastFetched] = useState(null);
    const fetchProcedures = useCallback(async (force = false) => {
        // Cache for 5 minutes unless forced
        const CACHE_DURATION = 5 * 60 * 1000;
        if (!force && lastFetched && Date.now() - lastFetched < CACHE_DURATION) {
            return procedures;
        }
        try {
            setLoading(true);
            const res = await getProcedures();
            setProcedures(res.data || []);
            setLastFetched(Date.now());
            return res.data || [];
        } catch (err) {
            console.error('Failed to fetch procedures:', err);
            return procedures; // Return cached on error
        } finally {
            setLoading(false);
        }
    }, [lastFetched, procedures]);
    // Initial fetch
    useEffect(() => {
        fetchProcedures();
    }, []);
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
