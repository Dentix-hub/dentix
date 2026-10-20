import { useState, useEffect, useCallback } from 'react';
import { getSmartTargetKindAndSurfaces } from '@/features/clinical-chart/domain/catalogDefinitions';
import { toothToNumber, fdiToPalmer, universalToPalmer } from '@/utils/toothUtils';

export function usePatientChartSelection({
    isPediatric,
    patient,
    effectiveTeethStatusRef,
    isTouchScrollingRef,
    executeClinicalActionRef,
    setNewTreatment,
    setIsTreatmentModalOpen,
    setSelectedToothCondition,
    getInitialTreatment,
}) {
    const [selectedTeeth, setSelectedTeeth] = useState([]);
    const [selectedSurfacesByTooth, setSelectedSurfacesByTooth] = useState({});
    const [isMultiSelectMode, setIsMultiSelectMode] = useState(false);
    const [activeToothKey, setActiveToothKey] = useState(null);
    const [isModifierKeyDown, setIsModifierKeyDown] = useState(false);

    // Sticky tool mode states
    const [activeStickyTool, setActiveStickyTool] = useState(null);
    const [stickyAppliedCount, setStickyAppliedCount] = useState(0);
    const [isQuickLauncherOpen, setIsQuickLauncherOpen] = useState(false);

    // Chart Plan Overlay states
    const [activeOverlayPlanId, setActiveOverlayPlanId] = useState(null);
    const [activeOverlayPhaseId, setActiveOverlayPhaseId] = useState(null);

    useEffect(() => {
        if (!activeStickyTool) return;
        const handleKeyDown = (e) => {
            if (e.key === 'Escape') {
                setActiveStickyTool(null);
                setStickyAppliedCount(0);
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [activeStickyTool]);

    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.shiftKey || e.ctrlKey || e.metaKey || e.key === 'Shift' || e.key === 'Control' || e.key === 'Meta') {
                setIsModifierKeyDown(true);
            }
        };
        const handleKeyUp = (e) => {
            if (!e.shiftKey && !e.ctrlKey && !e.metaKey) {
                setIsModifierKeyDown(false);
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        window.addEventListener('keyup', handleKeyUp);
        return () => {
            window.removeEventListener('keydown', handleKeyDown);
            window.removeEventListener('keyup', handleKeyUp);
        };
    }, []);

    const resolvedActiveTooth = activeToothKey || selectedTeeth[selectedTeeth.length - 1] || null;
    const activeSurfaces = (resolvedActiveTooth && selectedSurfacesByTooth[resolvedActiveTooth]) || [];

    const handleModalToothSelect = useCallback((number, notation = 'universal') => {
        const isFdiKey = notation === 'fdi';
        const fdi = isFdiKey ? Number.parseInt(number, 10) : toothToNumber(number);
        const current = effectiveTeethStatusRef.current[fdi]?.condition || 'Healthy';
        setSelectedToothCondition(current);
        const palmerPrefix = isFdiKey
            ? fdiToPalmer(fdi)
            : universalToPalmer(number, isPediatric);
        setNewTreatment({
            ...getInitialTreatment(),
            tooth_number: palmerPrefix,
            surface: '',
            surfaces: [],
            target_kind: 'tooth',
            default_price_list_id: patient?.default_price_list_id,
        });
        setIsTreatmentModalOpen(true);
    }, [isPediatric, patient, effectiveTeethStatusRef, setSelectedToothCondition, setNewTreatment, getInitialTreatment, setIsTreatmentModalOpen]);

    const handleToothClick = useCallback((number, notation = 'universal') => {
        if (isTouchScrollingRef?.current) {
            return;
        }

        const isFdiKey = notation === 'fdi';
        const fdi = isFdiKey ? Number.parseInt(number, 10) : toothToNumber(number);
        const toothKey = String(fdi);
        const current = effectiveTeethStatusRef.current[fdi]?.condition || 'Healthy';
        setSelectedToothCondition(current);

        // Sticky Tool Mode handling
        if (activeStickyTool && activeStickyTool.item) {
            const { item, targetKind, surfaces } = activeStickyTool;
            let effectiveTargetKind = targetKind;
            let effectiveSurfaces = surfaces || [];

            if (effectiveTargetKind === 'surface' && effectiveSurfaces.length === 0) {
                const smart = getSmartTargetKindAndSurfaces(item, toothKey, []);
                effectiveSurfaces = smart.surfaces.length > 0 ? smart.surfaces : [smart.defaultSurface || 'O'];
            }

            executeClinicalActionRef.current?.({
                item,
                toothKeys: [toothKey],
                targetKind: effectiveTargetKind,
                surfaces: effectiveSurfaces,
            })?.then((success) => {
                if (success) {
                    setStickyAppliedCount((prev) => prev + 1);
                }
            });

            setActiveToothKey(toothKey);
            return;
        }

        const isMulti = isMultiSelectMode || isModifierKeyDown;

        if (isMulti) {
            setSelectedTeeth(prev => {
                if (prev.includes(toothKey)) {
                    return prev.filter(k => k !== toothKey);
                }
                return [...prev, toothKey];
            });
            setActiveToothKey(toothKey);
        } else {
            setSelectedTeeth([toothKey]);
            setActiveToothKey(toothKey);
        }
    }, [isMultiSelectMode, isModifierKeyDown, activeStickyTool, isTouchScrollingRef, effectiveTeethStatusRef, setSelectedToothCondition, executeClinicalActionRef]);

    const handleSurfaceClick = useCallback((target) => {
        if (isTouchScrollingRef?.current) {
            return;
        }
        if (!target) return;
        const toothKey = String(target.toothKey || target.tooth_key || '');
        const surfaceCode = String(target.surfaceCode || target.surface_code || '').toUpperCase();
        if (!toothKey) return;

        const fdi = Number.parseInt(toothKey, 10);
        const current = effectiveTeethStatusRef.current[fdi]?.condition || 'Healthy';
        setSelectedToothCondition(current);

        // Sticky Tool Mode handling on surface
        if (activeStickyTool && activeStickyTool.item) {
            const { item } = activeStickyTool;
            executeClinicalActionRef.current?.({
                item,
                toothKeys: [toothKey],
                targetKind: 'surface',
                surfaces: [surfaceCode],
            })?.then((success) => {
                if (success) {
                    setStickyAppliedCount((prev) => prev + 1);
                }
            });

            setActiveToothKey(toothKey);
            return;
        }

        setSelectedTeeth(prev => {
            if (prev.includes(toothKey)) return prev;
            return isMultiSelectMode ? [...prev, toothKey] : [toothKey];
        });
        setActiveToothKey(toothKey);

        if (surfaceCode) {
            setSelectedSurfacesByTooth(prev => {
                const currentSurfaces = prev[toothKey] || [];
                const nextSurfaces = currentSurfaces.includes(surfaceCode)
                    ? currentSurfaces.filter(s => s !== surfaceCode)
                    : [...currentSurfaces, surfaceCode];
                return {
                    ...prev,
                    [toothKey]: nextSurfaces,
                };
            });
        }
    }, [isMultiSelectMode, activeStickyTool, isTouchScrollingRef, effectiveTeethStatusRef, setSelectedToothCondition, executeClinicalActionRef]);

    const handleToggleSurface = useCallback((surfaceCode) => {
        if (!resolvedActiveTooth) return;
        const surfaceUpper = String(surfaceCode).toUpperCase();
        setSelectedSurfacesByTooth(prev => {
            const currentSurfaces = prev[resolvedActiveTooth] || [];
            const nextSurfaces = currentSurfaces.includes(surfaceUpper)
                ? currentSurfaces.filter(s => s !== surfaceUpper)
                : [...currentSurfaces, surfaceUpper];
            return {
                ...prev,
                [resolvedActiveTooth]: nextSurfaces,
            };
        });
    }, [resolvedActiveTooth]);

    const handleRecordTreatmentFromSelection = useCallback(() => {
        const toothKey = resolvedActiveTooth || selectedTeeth[0];
        if (!toothKey) return;
        const fdi = Number.parseInt(toothKey, 10);
        const palmerPrefix = fdiToPalmer(fdi);
        const surfaces = selectedSurfacesByTooth[toothKey] || [];
        const surfaceUpper = surfaces.join('');

        setNewTreatment({
            ...getInitialTreatment(),
            tooth_number: palmerPrefix,
            surface: surfaceUpper,
            surfaces: [...surfaces],
            target_kind: surfaces.length > 0 ? 'surface' : 'tooth',
            default_price_list_id: patient?.default_price_list_id,
        });
        setIsTreatmentModalOpen(true);
    }, [resolvedActiveTooth, selectedTeeth, selectedSurfacesByTooth, patient, setNewTreatment, getInitialTreatment, setIsTreatmentModalOpen]);

    const handleClearSelection = useCallback(() => {
        setSelectedTeeth([]);
        setSelectedSurfacesByTooth({});
        setActiveToothKey(null);
    }, []);

    const handleRemoveToothFromSelection = useCallback((toothKey) => {
        setSelectedTeeth(prev => prev.filter(k => k !== toothKey));
        setSelectedSurfacesByTooth(prev => {
            const copy = { ...prev };
            delete copy[toothKey];
            return copy;
        });
        setActiveToothKey(prev => (prev === toothKey ? null : prev));
    }, []);

    const handleTogglePlanOverlay = useCallback((planId, phaseId = null) => {
        setActiveOverlayPlanId((prevPlanId) => {
            if (prevPlanId === planId && (phaseId === null || activeOverlayPhaseId === phaseId)) {
                setActiveOverlayPhaseId(null);
                return null;
            }
            setActiveOverlayPhaseId(phaseId);
            return planId;
        });
    }, [activeOverlayPhaseId]);

    return {
        selectedTeeth,
        setSelectedTeeth,
        selectedSurfacesByTooth,
        setSelectedSurfacesByTooth,
        isMultiSelectMode,
        setIsMultiSelectMode,
        activeToothKey,
        setActiveToothKey,
        isModifierKeyDown,
        activeStickyTool,
        setActiveStickyTool,
        stickyAppliedCount,
        setStickyAppliedCount,
        isQuickLauncherOpen,
        setIsQuickLauncherOpen,
        activeOverlayPlanId,
        setActiveOverlayPlanId,
        activeOverlayPhaseId,
        setActiveOverlayPhaseId,
        resolvedActiveTooth,
        activeSurfaces,
        handleModalToothSelect,
        handleToothClick,
        handleSurfaceClick,
        handleToggleSurface,
        handleRecordTreatmentFromSelection,
        handleClearSelection,
        handleRemoveToothFromSelection,
        handleTogglePlanOverlay,
    };
}
