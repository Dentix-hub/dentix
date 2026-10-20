import { useState, useMemo, useCallback } from 'react';
import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';
import { Search, Star, X, Check, Clock, Sparkles, MousePointerClick } from 'lucide-react';
import { useAuthStore } from '@/store/auth.store';
import { formatNumber } from '@/utils/formatters';
import {
    CANONICAL_FINDINGS,
    CANONICAL_PROCEDURES_BY_CODE,
    DEFAULT_FAVORITE_CODES,
    getSmartTargetKindAndSurfaces,
} from '../domain/catalogDefinitions';

const CATEGORY_LABELS = {
    restorative: { en: 'Restorative', ar: 'حشوات وترميم' },
    endodontic: { en: 'Endodontic', ar: 'علاج جذور' },
    prosthodontic: { en: 'Prosthodontic', ar: 'تركيبات واستعاضة' },
    implantology: { en: 'Implantology', ar: 'زراعة أسنان' },
    'oral-surgery': { en: 'Oral Surgery', ar: 'جراحة فم وأسنان' },
    clinic: { en: 'Clinic Procedures', ar: 'إجراءات العيادة' },
    finding: { en: 'Findings', ar: 'تشخيصات' },
};

export default function ChartQuickActionLauncher({
    selectedTeeth = [],
    selectedSurfacesByTooth = {},
    onAction,
    onActivateStickyTool,
    clinicProcedures = [],
    isLoading = false,
    onClose: _onClose,
}) {
    const { t, i18n } = useTranslation();
    const isRtl = i18n?.language?.startsWith('ar');
    const user = useAuthStore((state) => state.user);

    const tenantId = user?.tenant_id ?? 'default';
    const userId = user?.id ?? 'default';
    const favoritesStorageKey = `dentix_chart_favorites_${tenantId}_${userId}`;
    const recentsStorageKey = `dentix_chart_recents_${tenantId}_${userId}`;

    const [searchQuery, setSearchQuery] = useState('');
    const [showAllProcedures, setShowAllProcedures] = useState(false);

    // Initial favorites from localStorage; defaults to findings only
    const [favorites, setFavorites] = useState(() => {
        try {
            const stored = localStorage.getItem(favoritesStorageKey);
            if (!stored) return DEFAULT_FAVORITE_CODES;
            const parsed = JSON.parse(stored);
            return Array.isArray(parsed) ? parsed : DEFAULT_FAVORITE_CODES;
        } catch {
            return DEFAULT_FAVORITE_CODES;
        }
    });

    const [recents, setRecents] = useState(() => {
        try {
            const stored = localStorage.getItem(recentsStorageKey);
            if (!stored) return [];
            const parsed = JSON.parse(stored);
            return Array.isArray(parsed) ? parsed : [];
        } catch {
            return [];
        }
    });

    const [surfacePrompt, setSurfacePrompt] = useState(null);

    const activeToothKey = selectedTeeth[selectedTeeth.length - 1] || selectedTeeth[0] || null;
    const existingSurfaces = (activeToothKey && selectedSurfacesByTooth[activeToothKey]) || [];

    // Procedure items built exclusively from clinic procedures
    const procedureItems = useMemo(() => {
        if (!Array.isArray(clinicProcedures) || clinicProcedures.length === 0) {
            return [];
        }
        return clinicProcedures
            .filter((proc) => proc && proc.name)
            .map((proc) => {
                const canonicalCode = proc.canonical_code || null;
                const canonicalDef = canonicalCode
                    ? CANONICAL_PROCEDURES_BY_CODE.get(canonicalCode)
                    : null;
                const category = canonicalDef?.category || 'clinic';
                const allowed_target_kinds = canonicalDef?.allowed_target_kinds || ['tooth'];
                const requires_lab = Boolean(canonicalDef?.requires_lab);
                const rawPrice = Number(proc.price);
                const basePrice = !isNaN(rawPrice) && rawPrice > 0 ? rawPrice : null;
                const hasChartMapping = Boolean(canonicalCode);

                return {
                    key: `proc:${proc.id}`,
                    code: canonicalCode,
                    procedureId: proc.id,
                    name: proc.name,
                    nameAr: proc.name, // Clinic names are bilingual strings: display as-is, never split
                    kind: 'procedure',
                    category,
                    allowed_target_kinds,
                    requires_lab,
                    basePrice,
                    hasChartMapping,
                };
            });
    }, [clinicProcedures]);

    // Finding items from canonical findings (no price)
    const findingItems = useMemo(() => {
        return CANONICAL_FINDINGS.map((finding) => ({
            ...finding,
            key: finding.code,
            basePrice: null,
            hasChartMapping: true,
        }));
    }, []);

    const combinedActions = useMemo(() => {
        return [...findingItems, ...procedureItems];
    }, [findingItems, procedureItems]);

    // Indexed by item.key for safe favorite/recent retrieval without crashing on legacy codes
    const actionsByKey = useMemo(() => {
        const map = new Map();
        combinedActions.forEach((item) => map.set(item.key, item));
        return map;
    }, [combinedActions]);

    // Filter actions by search query
    const filteredActions = useMemo(() => {
        if (!searchQuery.trim()) return combinedActions;
        const q = searchQuery.toLowerCase().trim();
        return combinedActions.filter((item) => {
            const matchName = item.name.toLowerCase().includes(q);
            const matchNameAr = item.nameAr && item.nameAr.toLowerCase().includes(q);
            const matchCode = item.code && item.code.toLowerCase().includes(q);
            const matchCat = item.category && item.category.toLowerCase().includes(q);
            return matchName || matchNameAr || matchCode || matchCat;
        });
    }, [combinedActions, searchQuery]);

    // Save favorites to localStorage
    const toggleFavorite = useCallback((key, e) => {
        if (e && typeof e.stopPropagation === 'function') e.stopPropagation();
        setFavorites((prev) => {
            const isFav = prev.includes(key);
            const next = isFav ? prev.filter((k) => k !== key) : [...prev, key];
            try {
                localStorage.setItem(favoritesStorageKey, JSON.stringify(next));
            } catch {
                // Ignore storage errors
            }
            return next;
        });
    }, [favoritesStorageKey]);

    // Save action to recents in localStorage
    const pushToRecents = useCallback((key) => {
        setRecents((prev) => {
            const filtered = prev.filter((k) => k !== key);
            const next = [key, ...filtered].slice(0, 5);
            try {
                localStorage.setItem(recentsStorageKey, JSON.stringify(next));
            } catch {
                // Ignore storage errors
            }
            return next;
        });
    }, [recentsStorageKey]);

    const handleActivateSticky = (item, e) => {
        if (e && typeof e.stopPropagation === 'function') e.stopPropagation();
        pushToRecents(item.key);
        if (onActivateStickyTool) {
            const isSurfaceCapable = item.allowed_target_kinds?.includes('surface');
            const targetKind = isSurfaceCapable ? 'surface' : 'tooth';
            const defaultSurfaces = isSurfaceCapable
                ? (existingSurfaces.length > 0 ? existingSurfaces : ['O'])
                : [];
            onActivateStickyTool({
                item,
                targetKind,
                surfaces: defaultSurfaces,
            });
        }
    };

    // Handle clicking an action
    const handleActionClick = (item) => {
        if (selectedTeeth.length === 0) {
            // Procedure-first flow: activate tool for placement on chart
            handleActivateSticky(item);
            return;
        }

        const smart = getSmartTargetKindAndSurfaces(item, activeToothKey, existingSurfaces);

        // If surfaces are required and no surface was selected yet, prompt with smart default pre-selected
        if (smart.requiresSurfacePrompt) {
            setSurfacePrompt({
                item,
                surfaces: smart.surfaces,
                defaultSurface: smart.defaultSurface,
            });
            return;
        }

        // Apply immediately
        pushToRecents(item.key);
        if (onAction) {
            onAction({
                item,
                toothKeys: selectedTeeth,
                targetKind: smart.targetKind,
                surfaces: smart.surfaces,
            });
        }
    };

    const handleConfirmSurfacePrompt = () => {
        if (!surfacePrompt) return;
        const { item, surfaces } = surfacePrompt;
        pushToRecents(item.key);
        setSurfacePrompt(null);
        if (onAction) {
            onAction({
                item,
                toothKeys: selectedTeeth,
                targetKind: 'surface',
                surfaces: surfaces.length > 0 ? surfaces : [surfacePrompt.defaultSurface || 'O'],
            });
        }
    };

    const toggleSurfaceInPrompt = (surfaceCode) => {
        if (!surfacePrompt) return;
        setSurfacePrompt((prev) => {
            const exists = prev.surfaces.includes(surfaceCode);
            const nextSurfaces = exists
                ? prev.surfaces.filter((s) => s !== surfaceCode)
                : [...prev.surfaces, surfaceCode];
            return {
                ...prev,
                surfaces: nextSurfaces,
            };
        });
    };

    // Filter to known valid keys in current catalog (ignores old legacy keys like REST_COMPOSITE safely)
    const favoriteActions = useMemo(() => {
        return favorites
            .map((key) => actionsByKey.get(key))
            .filter(Boolean);
    }, [favorites, actionsByKey]);

    const recentActions = useMemo(() => {
        return recents
            .map((key) => actionsByKey.get(key))
            .filter(Boolean);
    }, [recents, actionsByKey]);

    // Group procedure items by category for the default view (first 8 visible, with show all expander)
    const proceduresByCategory = useMemo(() => {
        const visibleList = showAllProcedures ? procedureItems : procedureItems.slice(0, 8);
        const groups = new Map();
        visibleList.forEach((proc) => {
            const cat = proc.category || 'clinic';
            if (!groups.has(cat)) {
                groups.set(cat, []);
            }
            groups.get(cat).push(proc);
        });
        return Array.from(groups.entries()).map(([category, items]) => ({
            category,
            items,
        }));
    }, [procedureItems, showAllProcedures]);

    return (
        <div
            data-testid="chart-quick-action-launcher"
            className="space-y-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900"
        >
            {/* Header & Search */}
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-amber-500" aria-hidden="true" />
                    <h4 className="text-sm font-bold text-slate-800 dark:text-white">
                        {t('patient_details.chart.quick_launcher_title', 'Quick Actions')}
                    </h4>
                    {selectedTeeth.length > 0 && (
                        <span className="rounded-md bg-blue-50 px-2 py-0.5 text-xs font-semibold text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">
                            {t('patient_details.chart.active_tooth', 'Tooth')}: {selectedTeeth.join(', ')}
                        </span>
                    )}
                </div>

                <div className="relative flex-1 sm:max-w-xs">
                    <Search
                        className={`absolute top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 ${
                            isRtl ? 'right-3' : 'left-3'
                        }`}
                        aria-hidden="true"
                    />
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder={t('patient_details.chart.search_actions', 'Search procedures & findings... (/ or Alt+K)')}
                        data-testid="chart-quick-action-search"
                        className={`w-full min-h-11 rounded-xl border border-slate-200 bg-slate-50 text-xs text-slate-800 placeholder-slate-400 transition-colors focus:border-blue-500 focus:bg-white focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100 ${
                            isRtl ? 'pr-9 pl-8' : 'pl-9 pr-8'
                        }`}
                    />
                    {searchQuery && (
                        <button
                            type="button"
                            onClick={() => setSearchQuery('')}
                            aria-label={t('common.clear', 'Clear')}
                            className={`absolute top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 ${
                                isRtl ? 'left-2.5' : 'right-2.5'
                            }`}
                        >
                            <X className="h-4 w-4" />
                        </button>
                    )}
                </div>
            </div>

            {/* Surface Prompt Popover (when item requires surface and none selected) */}
            {surfacePrompt && (
                <div
                    data-testid="surface-prompt-popover"
                    className="rounded-xl border border-blue-200 bg-blue-50/70 p-3 dark:border-blue-900 dark:bg-blue-950/40"
                >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="space-y-0.5">
                            <span className="text-xs font-bold text-blue-900 dark:text-blue-200">
                                {t('patient_details.chart.select_surfaces', 'Select Surfaces')}: {isRtl ? surfacePrompt.item.nameAr : surfacePrompt.item.name}
                            </span>
                            <p className="text-[11px] text-blue-700 dark:text-blue-300">
                                {t('patient_details.chart.smart_default_hint', 'Smart default surface pre-selected based on anatomy')}
                            </p>
                        </div>
                        <div className="flex items-center gap-2">
                            <button
                                type="button"
                                onClick={() => setSurfacePrompt(null)}
                                className="min-h-11 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                            >
                                {t('common.cancel', 'Cancel')}
                            </button>
                            <button
                                type="button"
                                onClick={handleConfirmSurfacePrompt}
                                data-testid="confirm-action-button"
                                className="min-h-11 rounded-lg bg-blue-600 px-4 py-1.5 text-xs font-bold text-white shadow-sm hover:bg-blue-700"
                            >
                                <Check className="me-1 inline h-3.5 w-3.5" />
                                {t('patient_details.chart.apply', 'Apply')} ({surfacePrompt.surfaces.join('') || surfacePrompt.defaultSurface})
                            </button>
                        </div>
                    </div>

                    <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                        {['M', 'D', 'O', 'I', 'B', 'L', 'P'].map((surf) => {
                            const isSelected = surfacePrompt.surfaces.includes(surf);
                            return (
                                <button
                                    key={surf}
                                    type="button"
                                    onClick={() => toggleSurfaceInPrompt(surf)}
                                    aria-pressed={isSelected}
                                    data-testid={`prompt-surface-pill-${surf}`}
                                    className={`min-h-11 rounded-lg border px-3 py-1 text-xs font-bold transition-all ${
                                        isSelected
                                            ? 'border-blue-600 bg-blue-600 text-white shadow-sm'
                                            : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200'
                                    }`}
                                >
                                    {surf}
                                </button>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* If searching: show filtered results */}
            {searchQuery.trim() ? (
                <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs text-slate-500">
                        <span>{t('patient_details.chart.search_results', 'Search Results')} ({filteredActions.length})</span>
                    </div>
                    {filteredActions.length === 0 ? (
                        <div
                            data-testid="no-actions-found"
                            className="rounded-xl border border-dashed border-slate-200 p-4 text-center text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400"
                        >
                            {t('patient_details.chart.no_results', 'No matching actions found')}
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
                            {filteredActions.map((item) => (
                                <ActionCard
                                    key={item.key}
                                    item={item}
                                    isFavorite={favorites.includes(item.key)}
                                    onToggleFavorite={(e) => toggleFavorite(item.key, e)}
                                    onActivateSticky={(e) => handleActivateSticky(item, e)}
                                    onClick={() => handleActionClick(item)}
                                    isRtl={isRtl}
                                    t={t}
                                />
                            ))}
                        </div>
                    )}
                </div>
            ) : (
                /* Default view: Favorites -> Recents -> All procedures grouped by category */
                <div className="space-y-4">
                    {/* Favorites */}
                    {favoriteActions.length > 0 && (
                        <div data-testid="chart-quick-action-favorites" className="space-y-2">
                            <div className="flex items-center gap-1.5 text-xs font-bold text-slate-600 dark:text-slate-300">
                                <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-500" />
                                <span>{t('patient_details.chart.favorites', 'Favorites')}</span>
                            </div>
                            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
                                {favoriteActions.map((item) => (
                                    <ActionCard
                                        key={item.key}
                                        item={item}
                                        isFavorite={true}
                                        onToggleFavorite={(e) => toggleFavorite(item.key, e)}
                                        onActivateSticky={(e) => handleActivateSticky(item, e)}
                                        onClick={() => handleActionClick(item)}
                                        isRtl={isRtl}
                                        t={t}
                                    />
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Recents */}
                    {recentActions.length > 0 && (
                        <div data-testid="chart-quick-action-recents" className="space-y-2">
                            <div className="flex items-center gap-1.5 text-xs font-bold text-slate-600 dark:text-slate-300">
                                <Clock className="h-3.5 w-3.5 text-slate-400" />
                                <span>{t('patient_details.chart.recents', 'Recents')}</span>
                            </div>
                            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
                                {recentActions.map((item) => (
                                    <ActionCard
                                        key={`recent-${item.key}`}
                                        item={item}
                                        isFavorite={favorites.includes(item.key)}
                                        onToggleFavorite={(e) => toggleFavorite(item.key, e)}
                                        onActivateSticky={(e) => handleActivateSticky(item, e)}
                                        onClick={() => handleActionClick(item)}
                                        isRtl={isRtl}
                                        t={t}
                                        testIdPrefix="chart-quick-action-recent-item"
                                    />
                                ))}
                            </div>
                        </div>
                    )}

                    {/* All Procedures Grouped by Category */}
                    <div data-testid="chart-quick-action-all-procedures" className="space-y-3">
                        <div className="flex items-center justify-between text-xs font-bold text-slate-600 dark:text-slate-300">
                            <span>{t('patient_details.chart.all_procedures', 'All Procedures')}</span>
                            {procedureItems.length > 0 && (
                                <span className="text-slate-400 font-normal">
                                    ({procedureItems.length})
                                </span>
                            )}
                        </div>

                        {isLoading ? (
                            <div data-testid="chart-quick-action-loading" className="space-y-2 animate-pulse">
                                <div className="h-4 w-28 bg-slate-200 rounded dark:bg-slate-700"></div>
                                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
                                    {[1, 2, 3].map((i) => (
                                        <div key={i} className="h-11 bg-slate-100 rounded-xl dark:bg-slate-800"></div>
                                    ))}
                                </div>
                            </div>
                        ) : procedureItems.length === 0 ? (
                            <div
                                data-testid="no-clinic-procedures-hint"
                                className="rounded-xl border border-dashed border-slate-200 p-4 text-center text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400"
                            >
                                <p>{t('patient_details.chart.no_clinic_procedures', 'No clinic procedures configured.')}</p>
                                <p className="mt-1 text-[11px] text-slate-400">
                                    {t('patient_details.chart.configure_in_settings', 'Go to Settings → Procedures to add clinic procedures.')}
                                </p>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {proceduresByCategory.map(({ category, items }) => {
                                    const catLabel = isRtl
                                        ? CATEGORY_LABELS[category]?.ar || category
                                        : CATEGORY_LABELS[category]?.en || category;
                                    return (
                                        <div key={category} className="space-y-2">
                                            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                                                {catLabel}
                                            </div>
                                            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
                                                {items.map((item) => (
                                                    <ActionCard
                                                        key={item.key}
                                                        item={item}
                                                        isFavorite={favorites.includes(item.key)}
                                                        onToggleFavorite={(e) => toggleFavorite(item.key, e)}
                                                        onActivateSticky={(e) => handleActivateSticky(item, e)}
                                                        onClick={() => handleActionClick(item)}
                                                        isRtl={isRtl}
                                                        t={t}
                                                    />
                                                ))}
                                            </div>
                                        </div>
                                    );
                                })}

                                {procedureItems.length > 8 && (
                                    <div className="flex justify-center pt-1">
                                        <button
                                            type="button"
                                            data-testid="show-all-procedures-button"
                                            onClick={() => setShowAllProcedures((prev) => !prev)}
                                            className="min-h-11 rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-bold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 transition-colors"
                                        >
                                            {showAllProcedures
                                                ? t('patient_details.chart.show_less', 'Show less')
                                                : t('patient_details.chart.show_all_procedures', 'Show all ({{count}})', {
                                                      count: procedureItems.length,
                                                  })}
                                        </button>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

function ActionCard({
    item,
    isFavorite,
    onToggleFavorite,
    onActivateSticky,
    onClick,
    isRtl,
    t,
    testIdPrefix = 'chart-quick-action-item',
}) {
    const isFinding = item.kind === 'finding';
    const displayName = isFinding ? (isRtl ? item.nameAr || item.name : item.name) : item.name;
    const testIdKey = item.code || item.key;
    const formattedPrice = item.basePrice !== null ? formatNumber(item.basePrice, isRtl ? 'ar' : 'en') : null;

    return (
        <div
            data-testid={`${testIdPrefix}-${testIdKey}`}
            data-procedure-id={item.procedureId}
            role="button"
            tabIndex={0}
            onClick={onClick}
            onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onClick();
                }
            }}
            className="group flex min-h-11 items-center justify-between rounded-xl border border-slate-200 bg-slate-50/50 p-2.5 text-start transition-all hover:border-blue-400 hover:bg-blue-50/40 hover:shadow-sm dark:border-slate-800 dark:bg-slate-800/40 dark:hover:border-blue-700 dark:hover:bg-blue-950/20"
        >
            <div className="flex min-w-0 flex-col">
                <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="truncate text-xs font-bold text-slate-800 dark:text-slate-100">
                        {displayName}
                    </span>
                    <span
                        className={`rounded px-1.5 py-0.2 text-[10px] font-semibold ${
                            isFinding
                                ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
                                : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300'
                        }`}
                    >
                        {isFinding
                            ? t('patient_details.chart.finding_badge', 'Finding')
                            : t('patient_details.chart.procedure_badge', 'Procedure')}
                    </span>
                </div>
                <div className="flex items-center gap-1.5 flex-wrap text-[11px] text-slate-500 dark:text-slate-400">
                    {item.code && <span>{item.code}</span>}
                    {formattedPrice && (
                        <span className="font-mono">
                            {item.code ? `· ${formattedPrice}` : formattedPrice}
                        </span>
                    )}
                    {item.kind === 'procedure' && !item.hasChartMapping && (
                        <span
                            data-testid={`billing-only-tag-${testIdKey}`}
                            className="rounded px-1.5 py-0.2 text-[10px] font-semibold bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300"
                        >
                            {t('patient_details.chart.billing_only_tag', 'Billing only — not shown on chart/plan')}
                        </span>
                    )}
                </div>
            </div>

            <div className="ms-2 flex items-center gap-1 shrink-0">
                <button
                    type="button"
                    onClick={(e) => {
                        e.stopPropagation();
                        if (onActivateSticky) {
                            onActivateSticky(e);
                        }
                    }}
                    data-testid={`sticky-toggle-${testIdKey}`}
                    aria-label={t('patient_details.chart.activate_sticky', 'Activate sticky mode')}
                    title={t('patient_details.chart.activate_sticky', 'Activate sticky mode')}
                    className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-blue-100 hover:text-blue-600 dark:hover:bg-blue-900/40 dark:hover:text-blue-300"
                >
                    <MousePointerClick className="h-4 w-4" />
                </button>
                <button
                    type="button"
                    onClick={(e) => {
                        e.stopPropagation();
                        if (onToggleFavorite) {
                            onToggleFavorite(e);
                        }
                    }}
                    data-testid={`favorite-toggle-${testIdKey}`}
                    aria-label={
                        isFavorite
                            ? t('patient_details.chart.unstar_favorite', 'Remove from favorites')
                            : t('patient_details.chart.star_favorite', 'Add to favorites')
                    }
                    className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition-colors hover:text-amber-500"
                >
                    <Star
                        className={`h-4 w-4 ${
                            isFavorite ? 'fill-amber-400 text-amber-500' : 'text-slate-400'
                        }`}
                    />
                </button>
            </div>
        </div>
    );
}

ChartQuickActionLauncher.propTypes = {
    selectedTeeth: PropTypes.arrayOf(PropTypes.string),
    selectedSurfacesByTooth: PropTypes.object,
    onAction: PropTypes.func,
    onActivateStickyTool: PropTypes.func,
    clinicProcedures: PropTypes.arrayOf(PropTypes.object),
    isLoading: PropTypes.bool,
    onClose: PropTypes.func,
};
