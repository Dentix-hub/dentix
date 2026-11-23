import { useState, useEffect, useRef, useCallback } from 'react';
import {
    getCareSessionDraft,
    saveCareSessionDraft,
    deleteCareSessionDraft,
} from '@/api/patients';
import { formatApiError } from '@/utils/formatApiError';

const DEBOUNCE_DELAY_MS = 1500;

/**
 * useCareSessionDraft Hook (Slice S25 / G10-M17).
 * Provides debounced + event-flushed chairside draft autosave with server persistence,
 * serialized server saves, conflict detection and a reload guard for unacknowledged edits.
 */
export function useCareSessionDraft({
    patientId,
    careSessionId = null,
    initialData = null,
    enabled = true,
}) {
    const [draftData, setDraftData] = useState(initialData || {});
    const [versionId, setVersionId] = useState(1);
    const [status, setStatus] = useState('idle'); // 'idle' | 'unsaved' | 'saving' | 'saved' | 'error' | 'conflict'
    const [lastSavedAt, setLastSavedAt] = useState(null);
    const [errorMessage, setErrorMessage] = useState(null);
    const [hasConflict, setHasConflict] = useState(false);
    const [serverConflictDraft, setServerConflictDraft] = useState(null);
    const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

    const debounceTimerRef = useRef(null);
    const latestDataRef = useRef(draftData);
    const isMountedRef = useRef(true);
    const activeContextRef = useRef({ patientId, careSessionId });
    const versionIdRef = useRef(versionId);
    const generationTokenRef = useRef(0);
    const hasUserEditedRef = useRef(false);
    const saveToServerRef = useRef(null);

    // Durability & concurrency serialization refs
    const editRevisionRef = useRef(0);
    const acknowledgedRevisionRef = useRef(0);
    const inFlightSaveRef = useRef(null);
    const statusRef = useRef(status);
    const hasConflictRef = useRef(hasConflict);

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

    useEffect(() => {
        statusRef.current = status;
    }, [status]);

    useEffect(() => {
        hasConflictRef.current = hasConflict;
    }, [hasConflict]);

    const isDirty = useCallback(() => {
        return (
            editRevisionRef.current > acknowledgedRevisionRef.current ||
            Boolean(inFlightSaveRef.current) ||
            statusRef.current === 'error' ||
            statusRef.current === 'conflict'
        );
    }, []);

    // Reset local state synchronously when patient/session context changes and load server draft
    useEffect(() => {
        isMountedRef.current = true;
        generationTokenRef.current += 1;
        const currentToken = generationTokenRef.current;
        activeContextRef.current = { patientId, careSessionId };
        hasUserEditedRef.current = false;
        editRevisionRef.current = 0;
        acknowledgedRevisionRef.current = 0;
        inFlightSaveRef.current = null;

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
        statusRef.current = 'idle';
        setLastSavedAt(null);
        setErrorMessage(null);
        setHasConflict(false);
        hasConflictRef.current = false;
        setServerConflictDraft(null);
        setHasUnsavedChanges(false);

        if (!enabled || !patientId) return;

        let isCancelled = false;
        const currentPatientId = patientId;
        const currentCareSessionId = careSessionId;

        async function loadExistingDraft() {
            try {
                const res = await getCareSessionDraft(currentPatientId);
                if (isCancelled || !isMountedRef.current) return;
                if (
                    generationTokenRef.current !== currentToken ||
                    activeContextRef.current?.patientId !== currentPatientId ||
                    activeContextRef.current?.careSessionId !== currentCareSessionId
                ) {
                    return; // Stale context response, discard
                }

                const serverDraft = res?.data?.data || res?.data;
                if (serverDraft && serverDraft.draft_data) {
                    const loadedVersion = serverDraft.version_id || 1;
                    setVersionId(loadedVersion);
                    versionIdRef.current = loadedVersion;

                    // A previous visit's draft shares the author/patient version but its text belongs to that visit.
                    if (
                        serverDraft.care_session_id != null &&
                        String(serverDraft.care_session_id) !== String(currentCareSessionId)
                    ) return;

                    if (hasUserEditedRef.current) {
                        // User started typing before initial GET finished: preserve newly typed documentation
                        setDraftData((prev) => {
                            const merged = { ...serverDraft.draft_data, ...prev };
                            latestDataRef.current = merged;
                            if (debounceTimerRef.current) {
                                clearTimeout(debounceTimerRef.current);
                            }
                            debounceTimerRef.current = setTimeout(() => {
                                debounceTimerRef.current = null;
                                saveToServerRef.current?.().catch(() => {});
                            }, DEBOUNCE_DELAY_MS);
                            return merged;
                        });
                        setStatus('saving');
                        statusRef.current = 'saving';
                        setHasUnsavedChanges(true);
                    } else {
                        setDraftData(serverDraft.draft_data);
                        latestDataRef.current = serverDraft.draft_data;
                        setStatus('saved');
                        statusRef.current = 'saved';
                        setLastSavedAt(new Date(serverDraft.updated_at || Date.now()));
                        setHasUnsavedChanges(false);
                    }
                }
            } catch (err) {
                if (isCancelled || !isMountedRef.current) return;
                if (
                    generationTokenRef.current !== currentToken ||
                    activeContextRef.current?.patientId !== currentPatientId ||
                    activeContextRef.current?.careSessionId !== currentCareSessionId
                ) {
                    return;
                }
                // If 404, no server draft exists for this patient - keep clean state unless user typed
                if (err.response?.status === 404) {
                    if (!hasUserEditedRef.current) {
                        setStatus('idle');
                        statusRef.current = 'idle';
                    }
                    setErrorMessage(null);
                } else {
                    setErrorMessage(formatApiError(err, 'Failed to recover draft'));
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

    // Core serialized save function
    const saveToServer = useCallback(
        async (forceOverwrite = false) => {
            const targetToken = generationTokenRef.current;
            const targetPatientId = patientId;
            const targetCareSessionId = careSessionId;

            if (!targetPatientId || !enabled) return;
            if (
                generationTokenRef.current !== targetToken ||
                activeContextRef.current?.patientId !== targetPatientId ||
                activeContextRef.current?.careSessionId !== targetCareSessionId
            ) {
                return;
            }

            // Recheck the queue after each await: a newer save may have started while this caller waited.
            while (inFlightSaveRef.current) {
                try {
                    await inFlightSaveRef.current;
                } catch (error) {
                    if (!forceOverwrite) throw error;
                }
                if (
                    generationTokenRef.current !== targetToken ||
                    activeContextRef.current?.patientId !== targetPatientId ||
                    activeContextRef.current?.careSessionId !== targetCareSessionId
                ) {
                    return;
                }
            }

            const effectiveData = latestDataRef.current;
            const savingRevision = editRevisionRef.current;

            // Check if browser is offline
            const isOffline = typeof navigator !== 'undefined' && !navigator.onLine;
            if (isOffline) {
                setStatus('error');
                statusRef.current = 'error';
                setHasUnsavedChanges(true);
                setErrorMessage('Network offline. Cannot sync draft.');
                throw new Error('Network offline. Cannot sync draft.');
            }

            setStatus('saving');
            statusRef.current = 'saving';
            setErrorMessage(null);

            const runSave = (async () => {
                try {
                    const payload = {
                        draft_data: effectiveData,
                        care_session_id: targetCareSessionId,
                        expected_version_id: forceOverwrite ? undefined : versionIdRef.current,
                    };

                    const res = await saveCareSessionDraft(targetPatientId, payload);
                    const saved = res?.data?.data || res?.data;

                    if (
                        isMountedRef.current &&
                        generationTokenRef.current === targetToken &&
                        activeContextRef.current?.patientId === targetPatientId &&
                        activeContextRef.current?.careSessionId === targetCareSessionId
                    ) {
                        const nextVersion = saved?.version_id || versionIdRef.current + 1;
                        setVersionId(nextVersion);
                        versionIdRef.current = nextVersion;
                        acknowledgedRevisionRef.current = Math.max(
                            acknowledgedRevisionRef.current,
                            savingRevision
                        );
                        setHasConflict(false);
                        hasConflictRef.current = false;
                        setServerConflictDraft(null);
                        setLastSavedAt(new Date());

                        if (editRevisionRef.current > acknowledgedRevisionRef.current) {
                            // User kept typing while this save was in flight: keep unsaved state and schedule follow-up
                            setStatus('unsaved');
                            statusRef.current = 'unsaved';
                            setHasUnsavedChanges(true);
                        } else {
                            setStatus('saved');
                            statusRef.current = 'saved';
                            setHasUnsavedChanges(false);
                        }
                    }
                } catch (err) {
                    if (
                        !isMountedRef.current ||
                        generationTokenRef.current !== targetToken ||
                        activeContextRef.current?.patientId !== targetPatientId ||
                        activeContextRef.current?.careSessionId !== targetCareSessionId
                    ) {
                        return;
                    }

                    setHasUnsavedChanges(true);
                    if (err.response?.status === 409) {
                        // Stale draft version conflict from concurrent edit
                        const conflictBody = err.response?.data?.detail || err.response?.data?.data || err.response?.data;
                        setHasConflict(true);
                        hasConflictRef.current = true;
                        setServerConflictDraft(conflictBody);
                        setStatus('conflict');
                        statusRef.current = 'conflict';
                    } else {
                        setStatus('error');
                        statusRef.current = 'error';
                        setErrorMessage(formatApiError(err, 'Draft autosave failed'));
                    }
                    throw err;
                }
            })();

            inFlightSaveRef.current = runSave;
            try {
                await runSave;
            } finally {
                if (inFlightSaveRef.current === runSave) {
                    inFlightSaveRef.current = null;
                }
            }

            // If newer edits arrived while this request was in flight, flush them with the new version_id
            if (
                isMountedRef.current &&
                generationTokenRef.current === targetToken &&
                activeContextRef.current?.patientId === targetPatientId &&
                activeContextRef.current?.careSessionId === targetCareSessionId &&
                editRevisionRef.current > acknowledgedRevisionRef.current &&
                !hasConflictRef.current
            ) {
                if (debounceTimerRef.current) {
                    clearTimeout(debounceTimerRef.current);
                    debounceTimerRef.current = null;
                }
                await saveToServerRef.current?.();
            }
        },
        [patientId, careSessionId, enabled]
    );
    saveToServerRef.current = saveToServer;

    // Update draft data with debounced autosave
    const updateDraft = useCallback(
        (updater) => {
            hasUserEditedRef.current = true;
            editRevisionRef.current += 1;
            setHasUnsavedChanges(true);
            if (statusRef.current === 'idle' || statusRef.current === 'saved') {
                setStatus('unsaved');
                statusRef.current = 'unsaved';
            }

            setDraftData((prev) => {
                const next = typeof updater === 'function' ? updater(prev) : { ...prev, ...updater };
                latestDataRef.current = next;

                if (enabled) {
                    if (debounceTimerRef.current) {
                        clearTimeout(debounceTimerRef.current);
                    }
                    debounceTimerRef.current = setTimeout(() => {
                        debounceTimerRef.current = null;
                        saveToServerRef.current?.().catch(() => {});
                    }, DEBOUNCE_DELAY_MS);
                }

                return next;
            });
        },
        [enabled]
    );

    // Immediately trigger save and await acknowledgement of latest edits
    const saveNow = useCallback(async () => {
        if (debounceTimerRef.current) {
            clearTimeout(debounceTimerRef.current);
            debounceTimerRef.current = null;
        }
        return await saveToServer();
    }, [saveToServer]);

    // Protect pending edits on reload and begin saving when the document is hidden.
    useEffect(() => {
        if (!enabled || !patientId || typeof window === 'undefined') return;

        const handleBeforeUnload = (event) => {
            if (!isDirty()) return;
            event.preventDefault();
            // Required by Chromium/WebKit to trigger the native leave confirmation dialog
            event.returnValue = '';
        };

        const handleVisibilityChange = () => {
            if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
                if (editRevisionRef.current > acknowledgedRevisionRef.current && !hasConflictRef.current) {
                    if (debounceTimerRef.current) {
                        clearTimeout(debounceTimerRef.current);
                        debounceTimerRef.current = null;
                    }
                    saveToServerRef.current?.().catch(() => {});
                }
            }
        };

        window.addEventListener('beforeunload', handleBeforeUnload);
        document.addEventListener('visibilitychange', handleVisibilityChange);

        return () => {
            window.removeEventListener('beforeunload', handleBeforeUnload);
            document.removeEventListener('visibilitychange', handleVisibilityChange);
        };
    }, [enabled, patientId, isDirty]);

    // Conflict resolution: overwrite or accept server draft
    const resolveConflict = useCallback(
        async ({ overwrite }) => {
            if (overwrite) {
                await saveToServer(true);
            } else if (serverConflictDraft) {
                const serverData = serverConflictDraft.draft_data || serverConflictDraft.server_draft_data;
                const serverVersion = serverConflictDraft.version_id || serverConflictDraft.current_version_id || 1;
                if (serverData) {
                    setDraftData(serverData);
                    latestDataRef.current = serverData;
                    setVersionId(serverVersion);
                    versionIdRef.current = serverVersion;
                    acknowledgedRevisionRef.current = editRevisionRef.current;
                    setHasConflict(false);
                    hasConflictRef.current = false;
                    setServerConflictDraft(null);
                    setStatus('saved');
                    statusRef.current = 'saved';
                    setHasUnsavedChanges(false);
                }
            }
        },
        [saveToServer, serverConflictDraft]
    );

    // Discard draft (called on session finish or manual discard)
    const discardDraft = useCallback(async () => {
        const discardToken = ++generationTokenRef.current;
        const pendingSave = inFlightSaveRef.current;
        const targetPatientId = patientId;

        if (debounceTimerRef.current) {
            clearTimeout(debounceTimerRef.current);
            debounceTimerRef.current = null;
        }

        // Immediately reset local state for this patient
        if (
            generationTokenRef.current === discardToken &&
            activeContextRef.current?.patientId === targetPatientId
        ) {
            setDraftData({});
            latestDataRef.current = {};
            setVersionId(1);
            versionIdRef.current = 1;
            setStatus('idle');
            statusRef.current = 'idle';
            setLastSavedAt(null);
            setHasConflict(false);
            hasConflictRef.current = false;
            setServerConflictDraft(null);
            hasUserEditedRef.current = false;
            editRevisionRef.current = 0;
            acknowledgedRevisionRef.current = 0;
            inFlightSaveRef.current = null;
            setHasUnsavedChanges(false);
        }

        try {
            await pendingSave?.catch(() => {});
            if (
                generationTokenRef.current !== discardToken &&
                activeContextRef.current?.patientId === targetPatientId
            ) return;
            await deleteCareSessionDraft(targetPatientId);
        } catch {
            // Discard draft failure ignored
        }

        // Guard against late deletion clearing Patient B's state:
        // If user navigated away while deletion was pending, do NOT touch new context state
        if (
            !isMountedRef.current ||
            generationTokenRef.current !== discardToken ||
            activeContextRef.current?.patientId !== targetPatientId
        ) {
            return;
        }

        setDraftData({});
        latestDataRef.current = {};
        setVersionId(1);
        versionIdRef.current = 1;
        setStatus('idle');
        statusRef.current = 'idle';
        setLastSavedAt(null);
        setHasConflict(false);
        hasConflictRef.current = false;
        setServerConflictDraft(null);
        hasUserEditedRef.current = false;
        editRevisionRef.current = 0;
        acknowledgedRevisionRef.current = 0;
        inFlightSaveRef.current = null;
        setHasUnsavedChanges(false);
    }, [patientId]);

    return {
        draftData,
        versionId,
        updateDraft,
        saveNow,
        discardDraft,
        resolveConflict,
        status,
        hasUnsavedChanges,
        lastSavedAt,
        errorMessage,
        hasConflict,
        serverConflictDraft,
    };
}
