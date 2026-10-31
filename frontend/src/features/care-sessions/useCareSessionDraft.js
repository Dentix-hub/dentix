import { useState, useEffect, useRef, useCallback } from 'react';
import {
    getCareSessionDraft,
    saveCareSessionDraft,
    deleteCareSessionDraft,
} from '@/api/patients';

const DEBOUNCE_DELAY_MS = 1500;

/**
 * useCareSessionDraft Hook (Slice S25 / G10-M17).
 * Provides debounced chairside draft autosave, optimistic concurrency conflict detection,
 * offline fallback via localStorage, and draft discard on session finish.
 */
export function useCareSessionDraft({
    patientId,
    careSessionId = null,
    initialData = null,
    enabled = true,
}) {
    const [draftData, setDraftData] = useState(initialData || {});
    const [versionId, setVersionId] = useState(1);
    const [status, setStatus] = useState('idle'); // 'idle' | 'saving' | 'saved' | 'error' | 'conflict' | 'offline_saved'
    const [lastSavedAt, setLastSavedAt] = useState(null);
    const [errorMessage, setErrorMessage] = useState(null);
    const [hasConflict, setHasConflict] = useState(false);
    const [serverConflictDraft, setServerConflictDraft] = useState(null);

    const debounceTimerRef = useRef(null);
    const latestDataRef = useRef(draftData);
    const isMountedRef = useRef(true);

    const storageKey = `dentix_care_session_draft_${patientId}`;

    // Keep ref in sync
    useEffect(() => {
        latestDataRef.current = draftData;
    }, [draftData]);

    // Initial draft load from server (or offline local storage)
    useEffect(() => {
        isMountedRef.current = true;
        if (!enabled || !patientId) return;

        let isCancelled = false;

        async function loadExistingDraft() {
            try {
                const res = await getCareSessionDraft(patientId);
                const serverDraft = res?.data?.data || res?.data;
                if (!isCancelled && serverDraft && serverDraft.draft_data) {
                    setDraftData(serverDraft.draft_data);
                    setVersionId(serverDraft.version_id || 1);
                    setStatus('saved');
                    setLastSavedAt(new Date(serverDraft.updated_at || Date.now()));
                }
            } catch (err) {
                // If server 404 or network error, check offline local storage
                if (typeof window !== 'undefined') {
                    try {
                        const local = localStorage.getItem(storageKey);
                        if (local && !isCancelled) {
                            const parsed = JSON.parse(local);
                            setDraftData(parsed.draft_data || parsed);
                            setStatus('offline_saved');
                        }
                    } catch {}
                }
            }
        }

        loadExistingDraft();

        return () => {
            isCancelled = true;
            isMountedRef.current = false;
            if (debounceTimerRef.current) {
                clearTimeout(debounceTimerRef.current);
            }
        };
    }, [patientId, enabled, storageKey]);

    // Core save function
    const saveToServer = useCallback(
        async (dataToSave, forceOverwrite = false) => {
            if (!patientId || !enabled) return;

            // Check if browser is offline
            const isOffline = typeof navigator !== 'undefined' && !navigator.onLine;
            if (isOffline) {
                try {
                    localStorage.setItem(
                        storageKey,
                        JSON.stringify({ draft_data: dataToSave, updated_at: new Date().toISOString() })
                    );
                    setStatus('offline_saved');
                    setLastSavedAt(new Date());
                } catch {}
                return;
            }

            setStatus('saving');
            setErrorMessage(null);

            try {
                const payload = {
                    draft_data: dataToSave,
                    care_session_id: careSessionId,
                    expected_version_id: forceOverwrite ? undefined : versionId,
                };

                const res = await saveCareSessionDraft(patientId, payload);
                const saved = res?.data?.data || res?.data;

                if (isMountedRef.current) {
                    setVersionId(saved?.version_id || versionId + 1);
                    setStatus('saved');
                    setLastSavedAt(new Date());
                    setHasConflict(false);
                    setServerConflictDraft(null);

                    // Clean offline local storage when server sync succeeds
                    try {
                        localStorage.removeItem(storageKey);
                    } catch {}
                }
            } catch (err) {
                if (!isMountedRef.current) return;

                if (err.response?.status === 409) {
                    // Stale draft version conflict from concurrent edit
                    setHasConflict(true);
                    setServerConflictDraft(err.response?.data?.data || err.response?.data);
                    setStatus('conflict');
                } else {
                    // Save offline fallback on network or server error
                    try {
                        localStorage.setItem(
                            storageKey,
                            JSON.stringify({ draft_data: dataToSave, updated_at: new Date().toISOString() })
                        );
                        setStatus('offline_saved');
                    } catch {
                        setStatus('error');
                    }
                    setErrorMessage(err.response?.data?.detail || err.message || 'Draft autosave failed');
                }
            }
        },
        [patientId, careSessionId, versionId, enabled, storageKey]
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
        } catch {}

        try {
            localStorage.removeItem(storageKey);
        } catch {}

        if (isMountedRef.current) {
            setDraftData({});
            setVersionId(1);
            setStatus('idle');
            setLastSavedAt(null);
            setHasConflict(false);
        }
    }, [patientId, storageKey]);

    return {
        draftData,
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
