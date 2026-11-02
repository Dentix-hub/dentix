import PropTypes from 'prop-types';
import { Edit3, Ruler, Trash2 } from 'lucide-react';

function isCanalMeasurement(observation) {
    return (
        observation.structured_value?.length_mm != null ||
        observation.length_mm != null ||
        ['working_length', 'canal_length', 'canal_measurement'].includes(observation.observation_code)
    );
}

function fileSpecification(value) {
    const combined = /^#?(\d+)\s*\/\s*(0?\.\d+)$/.exec(String(value.maf || '').trim());
    return {
        size: combined
            ? `#${combined[1]}`
            : value.maf != null
              ? `#${String(value.maf).replace(/^#/, '')}`
              : '—',
        taper: value.taper ?? (combined ? Number(combined[2]) : '—'),
    };
}

/** A tooth/procedure group owns the table; individual clinical records stay intact. */
export default function ObservationSummary({
    observations = [],
    t = (key, fallback) => fallback || key,
    onAmend,
    onRemove,
    procedureLabels = {},
    testIdPrefix = 'observation',
    actionIdPrefix = 'amend-observation',
}) {
    const groups = new Map();
    const other = [];
    observations.forEach((observation, index) => {
        const row = { observation, index };
        if (!isCanalMeasurement(observation)) {
            other.push(row);
            return;
        }
        const tooth = observation.tooth_key || observation.structured_value?.tooth_key || '';
        const groupKey = `${observation.work_item_id ?? 'unassigned'}:${tooth}`;
        if (!groups.has(groupKey))
            groups.set(groupKey, { tooth, workItemId: observation.work_item_id, rows: [] });
        groups.get(groupKey).rows.push(row);
    });
    const action = (observation, index) => (
        <span className="inline-flex shrink-0 items-center gap-1">
            {observation.is_superseded ? (
                <span
                    className="rounded-control bg-amber-100 px-2 py-1 text-xs text-amber-900 dark:bg-amber-950 dark:text-amber-200"
                    title={observation.amendment_reason || ''}
                >
                    {t('care_session.amended_badge', 'Amended')}
                </span>
            ) : (
                onAmend && (
                    <button
                        type="button"
                        onClick={() => onAmend(observation)}
                        data-testid={`${actionIdPrefix}-${observation.id}`}
                        aria-label={t('care_session.amend_observation_title', 'Amend observation')}
                        className="inline-flex min-h-10 min-w-10 items-center justify-center rounded-control text-primary hover:bg-primary/10"
                    >
                        <Edit3 className="h-4 w-4" />
                    </button>
                )
            )}
            {onRemove && (
                <button
                    type="button"
                    onClick={() => onRemove(index)}
                    aria-label={t('care_session.remove_measurement', 'Remove measurement')}
                    data-testid={`remove-observation-${index}`}
                    className="inline-flex min-h-10 min-w-10 items-center justify-center rounded-control text-danger hover:bg-danger/10"
                >
                    <Trash2 className="h-4 w-4" />
                </button>
            )}
        </span>
    );
    if (!observations.length) return null;
    return (
        <div className="min-w-0 space-y-3" data-testid="observation-summary">
            {[...groups.entries()].map(([key, group]) => (
                <section
                    key={key}
                    className="min-w-0 overflow-hidden rounded-card border border-border bg-surface"
                    data-testid="canal-measurement-group"
                >
                    <header className="flex flex-wrap items-center justify-between gap-2 border-b border-border bg-surface-subtle px-3 py-2.5">
                        <h5 className="flex min-w-0 flex-wrap items-center gap-2 text-xs font-bold text-text-primary">
                            <Ruler className="h-4 w-4 shrink-0 text-primary" />
                            {t('care_session.canal_measurements', 'Canal measurements')}
                            {group.tooth && (
                                <span className="rounded-control bg-primary/10 px-2 py-1 text-primary">
                                    {t('care_sessions.tooth', 'Tooth')} <bdi dir="ltr">{group.tooth}</bdi>
                                </span>
                            )}
                            {procedureLabels[group.workItemId] && (
                                <span className="break-words font-normal text-text-secondary">
                                    {procedureLabels[group.workItemId]}
                                </span>
                            )}
                        </h5>
                        <span className="text-xs text-text-secondary">
                            {group.rows.length} {t('care_session.obs_added', 'measurements')}
                        </span>
                    </header>
                    <table
                        aria-label={t('care_session.canal_measurements', 'Canal measurements')}
                        className="w-full table-fixed text-start text-xs tabular-nums"
                    >
                        <thead className="text-text-secondary">
                            <tr>
                                {[
                                    t('care_session.canal_label', 'Canal'),
                                    t('care_session.length_mm', 'Length (mm)'),
                                    t('care_session.maf_size_short', 'File size'),
                                    t('care_session.taper_short', 'Taper'),
                                ].map((label) => (
                                    <th
                                        key={label}
                                        scope="col"
                                        className="px-2 py-2 text-start font-medium sm:px-3"
                                    >
                                        {label}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        {group.rows.map(({ observation, index }) => {
                            const value = observation.structured_value || {};
                            const file = fileSpecification(value);
                            const canal = observation.canal_id || value.canal_id || '—';
                            const root = observation.root_id || value.root_id;
                            const reference = String(
                                value.reference_point || observation.reference_point || '',
                            );
                            const length = value.length_mm ?? observation.length_mm ?? '—';
                            return (
                                <tbody
                                    key={observation.id ?? index}
                                    data-testid={`${testIdPrefix}-${observation.id ?? index}`}
                                    className="border-t border-border"
                                >
                                    <tr>
                                        <th
                                            scope="row"
                                            className="break-words px-2 pt-3 text-start font-bold text-primary sm:px-3"
                                        >
                                            <bdi dir="ltr">{canal}</bdi>
                                        </th>
                                        <td className="px-2 pt-3 font-semibold sm:px-3">
                                            <bdi dir="ltr">
                                                {length}
                                                {length !== '—' && ` ${t('care_session.length_unit', 'mm')}`}
                                            </bdi>
                                        </td>
                                        <td className="px-2 pt-3 sm:px-3">
                                            <bdi dir="ltr">{file.size}</bdi>
                                        </td>
                                        <td className="px-2 pt-3 sm:px-3">
                                            <bdi dir="ltr">{file.taper}</bdi>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td colSpan={4} className="px-2 pb-2 pt-1.5 sm:px-3">
                                            <div className="flex min-w-0 items-start justify-between gap-2">
                                                <div className="min-w-0 space-y-1 break-words text-text-secondary">
                                                    <p>
                                                        {root && (
                                                            <span>
                                                                {t(`care_session.roots.${root}`, root)}
                                                                {reference ? ' · ' : ''}
                                                            </span>
                                                        )}
                                                        {reference && (
                                                            <span>
                                                                {t(
                                                                    'care_session.ref_point',
                                                                    'Reference Point',
                                                                )}
                                                                :{' '}
                                                                {t(
                                                                    `care_session.reference_points.${reference.toLowerCase().replaceAll(' ', '_')}`,
                                                                    reference,
                                                                )}
                                                            </span>
                                                        )}
                                                    </p>
                                                    {observation.notes && (
                                                        <p className="whitespace-pre-wrap text-text-primary">
                                                            {observation.notes}
                                                        </p>
                                                    )}
                                                    {observation.is_reference && (
                                                        <p>
                                                            {t(
                                                                'care_session.carried_measurement',
                                                                'Carried from a previous visit',
                                                            )}
                                                        </p>
                                                    )}
                                                </div>
                                                {action(observation, index)}
                                            </div>
                                        </td>
                                    </tr>
                                </tbody>
                            );
                        })}
                    </table>
                </section>
            ))}
            {other.map(({ observation, index }) => {
                const value = observation.structured_value || {};
                const labels = {
                    measurement: t('care_session.obs_measurement', 'Measurement'),
                    shade: t('care_session.obs_shade', 'Shade'),
                    vitality: t('care_session.obs_vitality', 'Vitality'),
                };
                return (
                    <article
                        key={observation.id ?? index}
                        data-testid={`${testIdPrefix}-${observation.id ?? index}`}
                        className="flex min-w-0 items-start justify-between gap-3 rounded-card border border-border bg-surface p-3 text-xs"
                    >
                        <div className="min-w-0 space-y-1 break-words">
                            <p className="font-bold text-text-primary">
                                {labels[observation.observation_code] || observation.observation_code}
                                {observation.tooth_key && (
                                    <span className="ms-2 font-normal text-text-secondary">
                                        {t('care_sessions.tooth', 'Tooth')}{' '}
                                        <bdi dir="ltr">{observation.tooth_key}</bdi>
                                    </span>
                                )}
                            </p>
                            {value.value != null && (
                                <p className="text-sm text-text-primary">{String(value.value)}</p>
                            )}
                            {observation.notes && (
                                <p className="whitespace-pre-wrap text-text-secondary">{observation.notes}</p>
                            )}
                            {Object.entries(value)
                                .filter(
                                    ([field]) =>
                                        !['value', 'tooth_key', 'canal_id', 'root_id'].includes(field),
                                )
                                .map(([field, content]) => (
                                    <p key={field} className="text-text-secondary">
                                        {field}:{' '}
                                        {typeof content === 'object'
                                            ? Object.values(content || {}).join(', ')
                                            : String(content)}
                                    </p>
                                ))}
                        </div>
                        {action(observation, index)}
                    </article>
                );
            })}
        </div>
    );
}

ObservationSummary.propTypes = {
    observations: PropTypes.array,
    t: PropTypes.func,
    onAmend: PropTypes.func,
    onRemove: PropTypes.func,
    procedureLabels: PropTypes.object,
    testIdPrefix: PropTypes.string,
    actionIdPrefix: PropTypes.string,
};
