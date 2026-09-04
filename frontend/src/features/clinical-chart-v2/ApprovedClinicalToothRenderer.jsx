import { memo } from 'react';
import { APPROVED_PROCEDURE_SPRITES } from './approvedArtwork';
import { getHealthyAdultToothAsset } from './toothAssetRegistry';
import ProgrammaticToothArtwork from './ProgrammaticToothArtwork';
import { hasProgrammaticToothEffect } from './programmaticToothEffects';
import { normalizeClinicalToothState, parseFdiTooth, PROCEDURE_LIFECYCLE } from './toothTypes';

const ARABIC_PROCEDURE_LABELS = Object.freeze({
    caries: 'تسوس',
    composite: 'حشو تجميلي',
    amalgam: 'حشو أملغم',
    rct: 'علاج عصب',
    crown: 'تاج',
    implant: 'زرعة',
    bridge: 'جسر',
    missing: 'سن مفقود',
    fracture: 'كسر بالتاج',
});

const PROCEDURE_PRIORITY = Object.freeze([
    'missing', 'implant', 'rct', 'crown', 'bridge', 'fracture', 'caries', 'composite', 'amalgam',
]);

function resolveVisibleProcedures(state, showPlanned) {
    return state.procedures.filter((procedure) => (
        showPlanned || procedure.lifecycle !== PROCEDURE_LIFECYCLE.PLANNED
    ));
}

function resolvePrimaryProcedure(procedures) {
    return PROCEDURE_PRIORITY
        .map((type) => procedures.find((procedure) => procedure.type === type))
        .find(Boolean) || null;
}

const ApprovedClinicalToothRenderer = memo(function ApprovedClinicalToothRenderer({
    fdi,
    state = { procedures: [] },
    showPlanned = false,
    selected = false,
    showLabel = true,
    className = '',
}) {
    const tooth = parseFdiTooth(fdi);
    const clinicalState = normalizeClinicalToothState(state, fdi);
    const visibleProcedures = resolveVisibleProcedures(clinicalState, showPlanned);
    const primaryProcedure = resolvePrimaryProcedure(visibleProcedures);
    const healthyAsset = getHealthyAdultToothAsset(tooth.fdi);
    const hasProgrammaticEffect = primaryProcedure
        ? hasProgrammaticToothEffect({ fdi: tooth.fdi, type: primaryProcedure.type, surfaces: primaryProcedure.surfaces })
        : false;
    const visualLabel = hasProgrammaticEffect
        ? ARABIC_PROCEDURE_LABELS[primaryProcedure.type] || primaryProcedure.type
        : primaryProcedure
            ? `${ARABIC_PROCEDURE_LABELS[primaryProcedure.type] || primaryProcedure.type} — الأصل المخصص غير متاح`
        : 'سن سليم';

    return (
        <div
            className={`relative flex min-w-0 flex-col items-center rounded-xl px-1 py-2 transition ${
                selected ? 'bg-blue-50 ring-2 ring-blue-600' : 'hover:bg-slate-50'
            } ${className}`}
            data-fdi={tooth.fdi}
            data-procedure={primaryProcedure?.type || 'healthy'}
            data-lifecycle={primaryProcedure?.lifecycle || 'none'}
            data-asset-status={primaryProcedure && !hasProgrammaticEffect ? 'missing-programmatic-geometry' : 'ready'}
        >
            <div className="h-28 w-full sm:h-32" dir="ltr">
                {hasProgrammaticEffect ? (
                    <ProgrammaticToothArtwork
                        healthyAsset={healthyAsset}
                        procedure={primaryProcedure}
                        fdi={tooth.fdi}
                        testId={`tooth-artwork-${tooth.fdi}`}
                    />
                ) : (
                    <img
                        src={healthyAsset}
                        alt={`السن ${tooth.fdi}: ${visualLabel}`}
                        data-testid={`tooth-artwork-${tooth.fdi}`}
                        data-artwork-src={healthyAsset}
                        className="h-full w-full object-contain"
                        draggable="false"
                    />
                )}
            </div>

            {visibleProcedures.length > 1 && (
                <div className="absolute right-1 top-1 flex gap-0.5" aria-label={`${visibleProcedures.length} حالات سريرية`}>
                    {visibleProcedures.slice(0, 3).map((procedure) => (
                        <span
                            key={`${procedure.type}-${procedure.lifecycle}`}
                            className="h-2 w-2 rounded-full border border-white"
                            style={{ backgroundColor: APPROVED_PROCEDURE_SPRITES[procedure.type]?.color || '#64748b' }}
                            aria-hidden="true"
                        />
                    ))}
                </div>
            )}

            {showLabel && (
                <span className={`mt-1 font-mono text-xs font-semibold ${selected ? 'text-blue-700' : 'text-slate-600'}`}>
                    {tooth.fdi}
                </span>
            )}
        </div>
    );
});

export default ApprovedClinicalToothRenderer;
