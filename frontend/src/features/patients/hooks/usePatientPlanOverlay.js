import { useMemo } from 'react';

const PHASE_COLORS = [
    { border: '#3b82f6', bg: '#eff6ff', text: '#1d4ed8', badgeBg: '#2563eb', label: 'Phase 1' },
    { border: '#10b981', bg: '#ecfdf5', text: '#047857', badgeBg: '#059669', label: 'Phase 2' },
    { border: '#f59e0b', bg: '#fffbeb', text: '#b45309', badgeBg: '#d97706', label: 'Phase 3' },
    { border: '#8b5cf6', bg: '#f5f3ff', text: '#6d28d9', badgeBg: '#7c3aed', label: 'Phase 4' },
    { border: '#ec4899', bg: '#fdf2f8', text: '#be185d', badgeBg: '#db2777', label: 'Phase 5' },
];

/**
 * Builds the treatment-plan overlay consumed by DentalChartSVG (per-tooth badge/colors)
 * and PlanOverlayActiveBanner (plan title, phase chips).
 *
 * Teeth come from `item.work_item.targets[].tooth_key` (plan items carry no tooth_number).
 * Entry shape per tooth: { phaseId, phaseOrder, phaseName, phaseIndex, color, borderColor,
 * bgColor, badge, procedureCodes } — this is the contract the chart reads.
 */
export function usePatientPlanOverlay({ activeOverlayPlanId, activeOverlayPhaseId, treatmentPlans }) {
    return useMemo(() => {
        if (!activeOverlayPlanId || !treatmentPlans || treatmentPlans.length === 0) return null;
        const plan = treatmentPlans.find((p) => p.id === activeOverlayPlanId);
        if (!plan) return null;

        const teethMap = {};
        (plan.phases || []).forEach((ph, pIdx) => {
            if (activeOverlayPhaseId && ph.id !== activeOverlayPhaseId) return;
            const colorConfig = PHASE_COLORS[pIdx % PHASE_COLORS.length];
            (ph.items || []).forEach((item) => {
                const targets = item.work_item?.targets || [];
                targets.forEach((target) => {
                    if (target.tooth_key) {
                        const tk = String(target.tooth_key);
                        if (!teethMap[tk]) {
                            teethMap[tk] = {
                                phaseId: ph.id,
                                phaseOrder: ph.phase_order,
                                phaseName: ph.name,
                                phaseIndex: pIdx,
                                color: colorConfig.badgeBg,
                                borderColor: colorConfig.border,
                                bgColor: colorConfig.bg,
                                badge: `P${pIdx + 1}`,
                                procedureCodes: [item.work_item?.code].filter(Boolean),
                            };
                        } else if (item.work_item?.code && !teethMap[tk].procedureCodes.includes(item.work_item.code)) {
                            teethMap[tk].procedureCodes.push(item.work_item.code);
                        }
                    }
                });
            });
        });

        return {
            planId: plan.id,
            planTitle: plan.title,
            phaseId: activeOverlayPhaseId,
            teeth: teethMap,
            phases: (plan.phases || []).map((ph, idx) => ({
                id: ph.id,
                name: ph.name,
                colorConfig: PHASE_COLORS[idx % PHASE_COLORS.length],
            })),
        };
    }, [activeOverlayPlanId, activeOverlayPhaseId, treatmentPlans]);
}
