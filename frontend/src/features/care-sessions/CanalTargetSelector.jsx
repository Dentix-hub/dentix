import { useState, useMemo } from 'react';
import PropTypes from 'prop-types';
import { Plus, Check, GitBranch } from 'lucide-react';
import { getCanalAnatomyForTooth } from './canalAnatomy';

/**
 * Canal Target Selector (Slice S20 / G10-M09).
 * Allows chairside selection of root canals for a targeted tooth (e.g. MB, ML, D on Tooth 46).
 */
export default function CanalTargetSelector({
    toothKey,
    selectedCanals = [],
    onToggleCanal,
    t = (k, f) => f || k,
}) {
    const [customCanalName, setCustomCanalName] = useState('');
    const [customRootId, setCustomRootId] = useState('');

    const rootsAnatomy = useMemo(() => {
        return getCanalAnatomyForTooth(toothKey);
    }, [toothKey]);

    const isCanalSelected = (canalId, rootId) => {
        return selectedCanals.some(
            (c) => c.canalId?.toLowerCase() === canalId?.toLowerCase() && c.rootId === rootId
        );
    };

    const handleAddCustomCanal = (e) => {
        e.preventDefault();
        const trimmed = customCanalName.trim();
        if (!trimmed) return;
        const targetRoot = customRootId || rootsAnatomy[0]?.rootId || 'single';
        onToggleCanal({
            canalId: trimmed,
            rootId: targetRoot,
        });
        setCustomCanalName('');
    };

    return (
        <div
            data-testid="canal-target-selector"
            className="space-y-4 rounded-xl border border-slate-200 bg-slate-50/50 p-4 dark:border-slate-800 dark:bg-slate-900/50"
        >
            <div className="flex items-center justify-between border-b border-slate-200/80 pb-2.5 dark:border-slate-800">
                <div className="flex items-center gap-2">
                    <GitBranch className="h-4 w-4 text-blue-600 dark:text-blue-400" aria-hidden="true" />
                    <span className="text-sm font-bold text-slate-800 dark:text-slate-200">
                        {t('care_session.select_canals', 'Canal Targets')} (Tooth {toothKey})
                    </span>
                </div>
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
                    {selectedCanals.length} {t('care_session.canals_selected', 'selected')}
                </span>
            </div>

            <div className="space-y-3">
                {rootsAnatomy.map((root) => (
                    <div key={root.rootId} className="space-y-1.5">
                        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                            {root.rootLabel}
                        </span>
                        <div className="flex flex-wrap gap-2">
                            {root.defaultCanals.map((canalId) => {
                                const selected = isCanalSelected(canalId, root.rootId);
                                return (
                                    <button
                                        key={canalId}
                                        type="button"
                                        onClick={() => onToggleCanal({ canalId, rootId: root.rootId })}
                                        aria-pressed={selected}
                                        data-testid={`canal-chip-${canalId}`}
                                        className={`inline-flex min-h-10 items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-bold transition-all ${
                                            selected
                                                ? 'border-blue-600 bg-blue-600 text-white shadow-sm ring-1 ring-blue-500'
                                                : 'border-slate-300 bg-white text-slate-700 hover:border-slate-400 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'
                                        }`}
                                    >
                                        {selected && <Check className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />}
                                        <span>{canalId}</span>
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                ))}
            </div>

            {/* Custom Canal Addition */}
            <form onSubmit={handleAddCustomCanal} className="flex flex-wrap items-center gap-2 pt-2">
                <input
                    type="text"
                    value={customCanalName}
                    onChange={(e) => setCustomCanalName(e.target.value)}
                    placeholder={t('care_session.custom_canal_placeholder', 'Add canal (e.g. MM, MB3)...')}
                    className="min-h-10 flex-1 rounded-lg border border-slate-300 bg-white px-3 py-1 text-xs text-slate-800 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                    data-testid="custom-canal-input"
                />
                {rootsAnatomy.length > 1 && (
                    <select
                        value={customRootId || rootsAnatomy[0]?.rootId}
                        onChange={(e) => setCustomRootId(e.target.value)}
                        className="min-h-10 rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-xs text-slate-700 shadow-sm focus:border-blue-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                        data-testid="custom-canal-root-select"
                    >
                        {rootsAnatomy.map((r) => (
                            <option key={r.rootId} value={r.rootId}>
                                {r.rootLabel}
                            </option>
                        ))}
                    </select>
                )}
                <button
                    type="submit"
                    disabled={!customCanalName.trim()}
                    className="inline-flex min-h-10 items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-1 text-xs font-bold text-slate-700 transition-colors hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                    data-testid="add-custom-canal-button"
                >
                    <Plus className="h-3.5 w-3.5" aria-hidden="true" />
                    <span>{t('common.add', 'Add')}</span>
                </button>
            </form>
        </div>
    );
}

CanalTargetSelector.propTypes = {
    toothKey: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    selectedCanals: PropTypes.arrayOf(
        PropTypes.shape({
            canalId: PropTypes.string.isRequired,
            rootId: PropTypes.string.isRequired,
        })
    ).isRequired,
    onToggleCanal: PropTypes.func.isRequired,
    t: PropTypes.func,
};
