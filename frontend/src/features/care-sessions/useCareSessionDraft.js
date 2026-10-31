import { useState, useEffect, useRef, useCallback } from 'react';
import {
    getCareSessionDraft,
    saveCareSessionDraft,
    deleteCareSessionDraft,
} from '@/api/patients';

const DEBOUNCE_DELAY_MS = 1500;

/**
 * useCareSessionDraft Hook (Slice S25 / G10-M17).
 * Provides debounced chairside draft autosave with server persistence,
 * optimistic concurrency conflict detection, and draft discard on session finish.
 */
export function useCareSessionDraft({
    patientId,
    careSessionId = null,
    initialData = null,
    enabled = true,
}) {
    const [draftData, setDraftData] = useState(initialData || {});
    const [versionId, setVersionId] = useState(1);
    const [status, setStatus] = useState('idle'); // 'idle' | 'saving' | 'saved' | 'error' | 'conflict'
    const [lastSavedAt, setLastSavedAt] = useState(null);
    const [errorMessage, setErrorMessage] = useState(null);
    const [hasConflict, setHasConflict] = useState(false);
    const [serverConflictDraft, setServerConflictDraft] = useState(null);

    const debounceTimerRef = useRef(null);
    const latestDataRef = useRef(draftData);
    const isMountedRef = useRef(true);
    const activeContextRef = useRef({ patientId, careSessionId });
    const versionIdRef = useRef(versionId);

    // Track unmount lifecycle
    useEffect(() => {
        isMountedRef.current = true;
        return () => {
            isMountedRef.current = false;
        };
    }, []);

    // Keep refs in sync
    useEffect(() => {
        latestDataRef.current = draftData;
    }, [draftData]);

    useEffect(() => {
        versionIdRef.current = versionId;
    }, [versionId]);

    // Reset local state synchronously when patient/session context changes and load server draft
    useEffect(() => {
        isMountedRef.current = true;
        activeContextRef.current = { patientId, careSessionId };

        // Cancel any pending debounced autosaves from prior context
        if (debounceTimerRef.current) {
            clearTimeout(debounceTimerRef.current);
            debounceTimerRef.current = null;
        }

        // Immediately reset state to isolate patient/session boundaries
        const resetData = initialData || {};
        setDraftData(resetData);
        latestDataRef.current = resetData;
        setVersionId(1);
        versionIdRef.current = 1;
        setStatus('idle');
        setLastSavedAt(null);
        setErrorMessage(null);
        setHasConflict(false);
        setServerConflictDraft(null);

        if (!enabled || !patientId) return;

        let isCancelled = false;
        const currentPatientId = patientId;
        const currentCareSessionId = careSessionId;

        async function loadExistingDraft() {
            try {
                const res = await getCareSessionDraft(currentPatientId);
                if (isCancelled || !isMountedRef.current) return;
                if (
                    activeContextRef.current?.patientId !== currentPatientId ||
                    activeContextRef.current?.careSessionId !== currentCareSessionId
                ) {
                    return; // Stale context response, discard
                }

                const serverDraft = res?.data?.data || res?.data;
                if (serverDraft && serverDraft.draft_data) {
                    setDraftData(serverDraft.draft_data);
                    latestDataRef.current = serverDraft.draft_data;
                    const loadedVersion = serverDraft.version_id || 1;
                    setVersionId(loadedVersion);
                    versionIdRef.current = loadedVersion;
                    setStatus('saved');
                    setLastSavedAt(new Date(serverDraft.updated_at || Date.now()));
                }
            } catch (err) {
                if (isCancelled || !isMountedRef.current) return;
                if (
                    activeContextRef.current?.patientId !== currentPatientId ||
                    activeContextRef.current?.careSessionId !== currentCareSessionId
                ) {
                    return;
                }
                // If 404, no server draft exists for this patient - keep pristine reset state
                if (err.response?.status === 404) {
                    setStatus('idle');
                    setErrorMessage(null);
                } else {
                    setErrorMessage(err.response?.data?.detail || null);
                }
            }
        }

        loadExistingDraft();

        return () => {
            isCancelled = true;
            if (debounceTimerRef.current) {
                clearTimeout(debounceTimerRef.current);
                debounceTimerRef.current = null;
            }
        };
    }, [patientId, careSessionId, enabled, initialData]);

    // Core save function
    const saveToServer = useCallback(
        async (dataToSave, forceOverwrite = false) => {
            const targetPatientId = patientId;
            const targetCareSessionId = careSessionId;

            if (!targetPatientId || !enabled) return;
            if (
                activeContextRef.current?.patientId !== targetPatientId ||
                activeContextRef.current?.careSessionId !== targetCareSessionId
            ) {
                return;
            }

            // Check if browser is offline
            const isOffline = typeof navigator !== 'undefined' && !navigator.onLine;
            if (isOffline) {
                setStatus('error');
                setErrorMessage('Network offline. Cannot sync draft.');
                return;
            }

            setStatus('saving');
            setErrorMessage(null);

            try {
                const payload = {
                    draft_data: dataToSave,
                    care_session_id: targetCareSessionId,
                    expected_version_id: forceOverwrite ? undefined : versionIdRef.current,
                };

                const res = await saveCareSessionDraft(targetPatientId, payload);
                const saved = res?.data?.data || res?.data;

                if (
                    isMountedRef.current &&
                    activeContextRef.current?.patientId === targetPatientId &&
                    activeContextRef.current?.careSessionId === targetCareSessionId
                ) {
                    const nextVersion = saved?.version_id || versionIdRef.current + 1;
                    setVersionId(nextVersion);
                    versionIdRef.current = nextVersion;
                    setStatus('saved');
                    setLastSavedAt(new Date());
                    setHasConflict(false);
                    setServerConflictDraft(null);
                }
            } catch (err) {
                if (
                    !isMountedRef.current ||
                    activeContextRef.current?.patientId !== targetPatientId ||
                    activeContextRef.current?.careSessionId !== targetCareSessionId
                ) {
                    return;
                }

                if (err.response?.status === 409) {
                    // Stale draft version conflict from concurrent edit
                    setHasConflict(true);
                    setServerConflictDraft(err.response?.data?.data || err.response?.data);
                    setStatus('conflict');
                } else {
                    setStatus('error');
                    setErrorMessage(err.response?.data?.detail || err.message || 'Draft autosave failed');
                }
            }
        },
        [patientId, careSessionId, enabled]
    );

    // Update draft data with debounced autosave
    const updateDraft = useCallback(
        (updater) => {
            setDraftData((prev) => {
                const next = typeof updater === 'function' ? updater(prev) : { ...prev, ...updater };
                latestDataRef.current = next;

                if (enabled) {
                    if (debounceTimerRef.current) {
                        clearTimeout(debounceTimerRef.current);
                    }
                    debounceTimerRef.current = setTimeout(() => {
                        saveToServer(next);
                    }, DEBOUNCE_DELAY_MS);
                }

                return next;
            });
        },
        [enabled, saveToServer]
    );

    // Immediately trigger save
    const saveNow = useCallback(async () => {
        if (debounceTimerRef.current) {
            clearTimeout(debounceTimerRef.current);
        }
        await saveToServer(latestDataRef.current);
    }, [saveToServer]);

    // Conflict resolution: overwrite or accept server draft
    const resolveConflict = useCallback(
        async ({ overwrite }) => {
            if (overwrite) {
                await saveToServer(latestDataRef.current, true);
            } else if (serverConflictDraft && serverConflictDraft.draft_data) {
                setDraftData(serverConflictDraft.draft_data);
                setVersionId(serverConflictDraft.version_id || 1);
                setHasConflict(false);
                setServerConflictDraft(null);
                setStatus('saved');
            }
        },
        [saveToServer, serverConflictDraft]
    );

    // Discard draft (called on session finish or manual discard)
    const discardDraft = useCallback(async () => {
        if (debounceTimerRef.current) {
            clearTimeout(debounceTimerRef.current);
        }
        try {
            await deleteCareSessionDraft(patientId);
        } catch {
            // Discard draft failure ignored
        }

        if (isMountedRef.current) {
            setDraftData({});
            setVersionId(1);
            setStatus('idle');
            setLastSavedAt(null);
            setHasConflict(false);
        }
    }, [patientId]);

    return {
        draftData,
        versionId,
        updateDraft,
        saveNow,
        discardDraft,
        resolveConflict,
        status,
        lastSavedAt,
        errorMessage,
        hasConflict,
        serverConflictDraft,
    };
}
