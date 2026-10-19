import { useMemo } from 'react';

const PHASE_COLORS = [
    { border: '#3b82f6', bg: 'rgba(59, 130, 246, 0.15)', name: 'blue' },
    { border: '#10b981', bg: 'rgba(16, 185, 129, 0.15)', name: 'green' },
    { border: '#f59e0b', bg: 'rgba(245, 158, 11, 0.15)', name: 'amber' },
    { border: '#8b5cf6', bg: 'rgba(139, 92, 246, 0.15)', name: 'purple' },
];

export function usePatientPlanOverlay({ activeOverlayPlanId, activeOverlayPhaseId, treatmentPlans }) {
    return useMemo(() => {
        if (!activeOverlayPlanId) return null;
        const activePlan = treatmentPlans.find((p) => p.id === activeOverlayPlanId);
        if (!activePlan) return null;

        const phases = activePlan.phases || [];
        const filteredPhases = activeOverlayPhaseId
            ? phases.filter((ph) => ph.id === activeOverlayPhaseId)
            : phases;

        const teeth = {};

        filteredPhases.forEach((ph, pIdx) => {
            const colorCfg = PHASE_COLORS[pIdx % PHASE_COLORS.length];
            (ph.items || []).forEach((item) => {
                const toothNum = item.tooth_number;
                if (!toothNum) return;
                const toothKey = String(toothNum);
                if (!teeth[toothKey]) {
                    teeth[toothKey] = {
                        planId: activePlan.id,
                        planTitle: activePlan.title,
                        phaseId: ph.id,
                        phaseName: ph.name,
                        procedureName: item.procedure_name || item.procedure_code,
                        colorConfig: colorCfg,
                        items: [],
                    };
                }
                teeth[toothKey].items.push({
                    id: item.id,
                    procedureName: item.procedure_name || item.procedure_code,
                    status: item.status,
                    phaseId: ph.id,
                    phaseName: ph.name,
                    colorConfig: colorCfg,
                });
            });
        });

        return {
            planId: activePlan.id,
            planTitle: activePlan.title,
            activePhaseId: activeOverlayPhaseId,
            teeth,
            phases: phases.map((ph, idx) => ({
                id: ph.id,
                name: ph.name,
                colorConfig: PHASE_COLORS[idx % PHASE_COLORS.length],
            })),
        };
    }, [activeOverlayPlanId, activeOverlayPhaseId, treatmentPlans]);
}
