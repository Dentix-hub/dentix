import { memo } from 'react';
import { MAX_VISIBLE_PROCEDURE_MARKERS } from '../domain/clinicalChartProjection';
import { resolveMarkerPaletteColor } from '../domain/procedureChartPalette';

const inferArchFromToothKey = (toothKey) => {
    const firstDigit = String(toothKey || '')[0];
    return ['3', '4', '7', '8'].includes(firstDigit) ? 'lower' : 'upper';
};

/**
 * Renders non-canonical procedure markers (template `MARKER`, Decision D3)
 * near the outer edge of a tooth crown as a separate visual component.
 *
 * Contract:
 * - Not a `VISUAL_LAYER_SEQUENCE` role; rendered alongside the crown by `DentalChartSVG`.
 * - `pointer-events: none` so it never intercepts tooth or surface selection clicks.
 * - Accessible `<title>` containing the procedure name for every marker.
 * - Distinct multi-ring + inner-diamond silhouette so markers are never color-only.
 * - Caps visible markers to `MAX_VISIBLE_PROCEDURE_MARKERS` (3) and shows `+N` overflow.
 * - Respects upper vs lower arch orientation and isolates LTR numeric overflow in RTL shells.
 */
const ToothProcedureMarkers = memo(function ToothProcedureMarkers({
    toothKey,
    arch,
    markers = [],
    overflowCount = 0,
}) {
    if (!Array.isArray(markers) || markers.length === 0) {
        return null;
    }

    const resolvedArch = arch === 'lower' || arch === 'upper'
        ? arch
        : inferArchFromToothKey(toothKey);
    const visibleMarkers = markers.slice(0, MAX_VISIBLE_PROCEDURE_MARKERS);
    const extraFromArray = Math.max(0, markers.length - visibleMarkers.length);
    const effectiveOverflow = Math.max(0, Number(overflowCount || 0) + extraFromArray);

    // Upper arch: roots are at top (y=0..48), crown outer occlusal edge is at bottom (y=54).
    // Lower arch: roots are at bottom, crown outer occlusal edge is at top (y=5).
    const cy = resolvedArch === 'lower' ? 5 : 54;
    const totalSlots = visibleMarkers.length + (effectiveOverflow > 0 ? 1 : 0);
    const step = totalSlots >= 4 ? 9.5 : 10.5;
    const startX = 25 - ((totalSlots - 1) * step) / 2;

    return (
        <svg
            aria-label={`Tooth ${toothKey} procedure markers`}
            className="pointer-events-none"
            data-arch={resolvedArch}
            data-edge={resolvedArch === 'lower' ? 'top' : 'bottom'}
            data-layer="procedure-markers"
            data-marker-count={visibleMarkers.length}
            data-overflow-count={effectiveOverflow}
            data-testid={`tooth-procedure-markers-${toothKey}`}
            data-tooth-key={toothKey}
            height="60"
            pointerEvents="none"
            viewBox="0 0 50 60"
            width="50"
            x="0"
            y="0"
        >
            <g
                data-marker-cy={cy}
                direction="ltr"
                pointerEvents="none"
            >
                {visibleMarkers.map((marker, index) => {
                    const cx = Number((startX + index * step).toFixed(2));
                    const rawColorKey = marker?.colorKey ?? marker?.color_key ?? null;
                    const palette = resolveMarkerPaletteColor(rawColorKey);
                    const procedureName = String(
                        marker?.procedureName ?? marker?.procedure_name ?? 'Procedure',
                    );
                    const markerId = String(
                        marker?.markerId ?? marker?.marker_id ?? `${toothKey}-marker-${index + 1}`,
                    );
                    const phase = String(marker?.phase ?? 'completed');
                    const isPlanned = phase === 'planned';
                    const isActive = phase === 'active';

                    return (
                        <g
                            data-color-key={palette.key}
                            data-marker-id={markerId}
                            data-phase={phase}
                            data-testid={`tooth-procedure-marker-${toothKey}-${index}`}
                            key={markerId}
                            pointerEvents="none"
                        >
                            <title>{procedureName}</title>
                            <circle
                                cx={cx}
                                cy={cy}
                                data-marker-halo="true"
                                fill="#ffffff"
                                pointerEvents="none"
                                r="4.1"
                                stroke={palette.stroke}
                                strokeDasharray={isPlanned ? '2 1' : (isActive ? '1.5 1' : undefined)}
                                strokeWidth="1.2"
                            />
                            <circle
                                cx={cx}
                                cy={cy}
                                data-marker-dot="true"
                                fill={palette.fill}
                                pointerEvents="none"
                                r="2.7"
                                stroke={palette.stroke}
                                strokeWidth="0.9"
                            />
                            <path
                                d={`M${cx},${cy - 1.2} L${cx + 1.2},${cy} L${cx},${cy + 1.2} L${cx - 1.2},${cy} Z`}
                                data-marker-glyph="diamond"
                                fill="#ffffff"
                                pointerEvents="none"
                            />
                        </g>
                    );
                })}
                {effectiveOverflow > 0 && (() => {
                    const overflowX = Number((startX + visibleMarkers.length * step).toFixed(2));
                    return (
                        <g
                            data-overflow-count={effectiveOverflow}
                            data-testid={`tooth-procedure-marker-overflow-${toothKey}`}
                            pointerEvents="none"
                        >
                            <title>{`+${effectiveOverflow}`}</title>
                            <rect
                                fill="#ffffff"
                                height="8.4"
                                pointerEvents="none"
                                rx="4.2"
                                stroke="#334155"
                                strokeWidth="1"
                                width="11.5"
                                x={overflowX - 5.75}
                                y={cy - 4.2}
                            />
                            <text
                                direction="ltr"
                                fill="#334155"
                                fontSize="5.8"
                                fontWeight="700"
                                pointerEvents="none"
                                textAnchor="middle"
                                unicodeBidi="isolate"
                                x={overflowX}
                                y={cy + 2}
                            >
                                {`+${effectiveOverflow}`}
                            </text>
                        </g>
                    );
                })()}
            </g>
        </svg>
    );
});

export default ToothProcedureMarkers;
