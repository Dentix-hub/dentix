import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { getProcedures } from '@/api';
import { getProcedureFinancials } from '@/api/financials';
import { updateMaterial } from '@/api/inventory';
import { Package, Search, TrendingUp, AlertTriangle } from 'lucide-react';
const ProcedureCostAnalysis = () => {
    const { t } = useTranslation();
    const [procedures, setProcedures] = useState([]);
    const [selectedProcedure, setSelectedProcedure] = useState(null);
    const [analysis, setAnalysis] = useState(null);
    const [loading, setLoading] = useState(false);
    const [activeTab, setActiveTab] = useState('analysis'); // analysis, coverage
    useEffect(() => {
        loadProcedures();
    }, []);
    useEffect(() => {
        if (selectedProcedure) {
            loadFinancials(selectedProcedure);
        } else {
            setAnalysis(null);
        }
    }, [selectedProcedure]);
    const loadProcedures = async () => {
        try {
            const res = await getProcedures();
            setProcedures(res.data || []);
        } catch (err) {
            console.error("Failed to load procedures", err);
        }
    };
    const loadFinancials = async (procId) => {
        setLoading(true);
        try {
            const res = await getProcedureFinancials(procId);
            setAnalysis(res.data);
        } catch (err) {
            console.error("Failed to load financials", err);
            setAnalysis(null);
        } finally {
            setLoading(false);
        }
    };
    return (
        <div className="bg-white dark:bg-slate-800 rounded-3xl p-6 shadow-sm border border-slate-100 dark:border-slate-700 animate-in fade-in slide-in-from-bottom-4 duration-700">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
                <div>
                    <h2 className="text-xl font-bold flex items-center gap-2 text-slate-800 dark:text-white">
                        <TrendingUp className="text-indigo-600" />
                        {t('analytics.procedure_analysis.title')}
                    </h2>
                    <p className="text-sm text-slate-500 mt-1">{t('analytics.procedure_analysis.subtitle')}</p>
                </div>
                <div className="w-full md:w-64">
                    <select
                        className="w-full p-2.5 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl font-bold text-sm outline-none focus:border-indigo-500"
                        onChange={(e) => setSelectedProcedure(e.target.value)}
                        value={selectedProcedure || ''}
                    >
                        <option value="">{t('analytics.procedure_analysis.select_placeholder')}</option>
                        {procedures.map(p => (
                            <option key={p.id} value={p.id}>{p.name}</option>
                        ))}
                    </select>
                </div>
            </div>
            {!selectedProcedure ? (
                <div className="text-center py-12 text-slate-400 bg-slate-50 dark:bg-slate-900/50 rounded-2xl border border-dashed border-slate-200">
                    <Search className="mx-auto mb-2 opacity-50" size={32} />
                    <p>{t('analytics.procedure_analysis.empty_state')}</p>
                </div>
            ) : loading ? (
                <div className="py-12 text-center text-slate-500 animate-pulse">{t('analytics.procedure_analysis.loading')}</div>
            ) : analysis ? (
                <>
                    {/* Tabs Header */}
                    <div className="flex gap-2 border-b mb-6 overflow-x-auto">
                        <button
                            onClick={() => setActiveTab('analysis')}
                            className={`pb-3 px-4 text-sm font-bold transition-colors border-b-2 whitespace-nowrap ${activeTab === 'analysis' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
                        >
                            {t('analytics.procedure_analysis.tabs.cost_smart')}
                        </button>
                        <button
                            onClick={() => setActiveTab('coverage')}
                            className={`pb-3 px-4 text-sm font-bold transition-colors border-b-2 whitespace-nowrap ${activeTab === 'coverage' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
                        >
                            {t('analytics.procedure_analysis.tabs.consumption')}
                        </button>
                    </div>
                    {/* ANALYSIS TAB */}
                    {activeTab === 'analysis' && (
                        <div className="animate-in fade-in slide-in-from-right-4 space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                                {/* Service Price */}
                                <div className="bg-slate-50 dark:bg-slate-900/50 p-4 rounded-2xl border border-slate-100 dark:border-slate-700 text-center shadow-sm">
                                    <div className="text-xs text-slate-500 font-bold mb-1">{t('analytics.procedure_analysis.metrics.service_price')}</div>
                                    <div className="text-2xl font-black text-slate-800 dark:text-white">{analysis.current_price}</div>
                                    <div className="text-[10px] text-slate-400">{t('analytics.general_analysis.currency')}</div>
                                </div>
                                {/* Actual Cost (AI) */}
                                <div className="bg-indigo-50 dark:bg-indigo-900/20 p-4 rounded-2xl border border-indigo-100 dark:border-indigo-800 text-center shadow-sm relative overflow-hidden">
                                    <div className="absolute top-0 right-0 bg-indigo-600 text-white text-[9px] px-2 py-0.5 rounded-bl-lg">AI Learn</div>
                                    <div className="text-xs text-indigo-800 dark:text-indigo-300 font-bold mb-1">{t('analytics.procedure_analysis.metrics.actual_cost')}</div>
                                    <div className="text-2xl font-black text-indigo-700 dark:text-indigo-400">{analysis.total_actual_cost}</div>
                                    <div className="text-[10px] text-indigo-400">{t('analytics.procedure_analysis.metrics.actual_margin')}</div>
                                </div>
                                {/* Actual Profit */}
                                <div className={`p-4 rounded-2xl border text-center shadow-sm ${analysis.actual_profit_margin < 0 ? 'bg-red-50 border-red-100 text-red-700' : 'bg-emerald-50 border-emerald-100 text-emerald-700'}`}>
                                    <div className="text-xs font-bold mb-1 opacity-80">{t('analytics.procedure_analysis.metrics.actual_profit')}</div>
                                    <div className="text-2xl font-black mb-1">{analysis.actual_profit_margin}</div>
                                    <div className="text-[10px] opacity-70">{analysis.actual_margin_percentage}%</div>
                                </div>
                            </div>
                            {/* Suggestions */}
                            {analysis.actual_margin_percentage < 30 && (
                                <div className="bg-amber-50 border border-amber-200 p-4 rounded-xl flex gap-3 items-start text-amber-800">
                                    <AlertTriangle className="shrink-0" size={20} />
                                    <div>
                                        <h4 className="font-bold">{t('analytics.procedure_analysis.alerts.low_margin')}</h4>
                                        <p className="text-sm mt-1">
                                            {t('analytics.procedure_analysis.alerts.low_margin_desc')}
                                        </p>
                                    </div>
                                </div>
                            )}
                            <div className="bg-slate-50 dark:bg-slate-900/30 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
                                <h4 className="font-bold text-sm text-slate-600 dark:text-slate-300 mb-3 flex justify-between">
                                    <span>{t('analytics.procedure_analysis.comparison.title')}</span>
                                    <span className="text-xs font-normal bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300 px-2 py-1 rounded">{t('analytics.procedure_analysis.comparison.ai_samples')}: {analysis.breakdown?.[0]?.sample_size || 0}+</span>
                                </h4>
                                <div className="space-y-2">
                                    {(analysis.breakdown || []).map((item, idx) => (
                                        <div key={idx} className="flex flex-col sm:flex-row justify-between items-center text-sm p-3 bg-white dark:bg-slate-800 rounded-lg border border-slate-100 dark:border-slate-700 hover:shadow-sm transition-shadow gap-3">
                                            <div className="flex-1 text-center sm:text-right w-full">
                                                <div className="font-bold text-slate-700 dark:text-slate-200">{item.material_name}</div>
                                                <div className="text-xs text-slate-400 mt-0.5">{item.unit_cost} ج.م / {item.base_unit}</div>
                                            </div>
                                            {/* Comparison Grid */}
                                            <div className="flex bg-slate-50 dark:bg-slate-900 rounded-lg p-1 gap-4 text-center w-full sm:w-auto justify-center">
                                                <div className="px-2 border-r border-slate-200 dark:border-slate-700">
                                                    <div className="text-[10px] text-slate-400">{t('analytics.procedure_analysis.comparison.weight_score')}</div>
                                                    <div className="font-bold text-slate-600 dark:text-slate-300">{item.weight_used} <span className="text-[9px] font-normal">{t('analytics.procedure_analysis.comparison.points')}</span></div>
                                                    {/* Cost removed as Score is unitless */}
                                                </div>
                                                <div className="px-2">
                                                    <div className="text-[10px] text-indigo-500 font-bold">{t('analytics.procedure_analysis.comparison.ai_projected')}</div>
                                                    <div className="font-bold text-indigo-700 dark:text-indigo-400">{item.actual_usage} <span className="text-[9px] font-normal">{item.base_unit}</span></div>
                                                    <div className="text-[10px] text-indigo-600 dark:text-indigo-500">{item.actual_cost} {t('analytics.general_analysis.currency')}</div>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}
                    {/* COVERAGE TAB */}
                    {activeTab === 'coverage' && (
                        <div className="animate-in fade-in slide-in-from-right-4">
                            <div className="bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-100 dark:border-indigo-800 p-4 rounded-xl mb-6">
                                <h4 className="font-bold text-indigo-900 dark:text-indigo-100 flex items-center gap-2 mb-2">
                                    <Package size={18} />
                                    {t('analytics.procedure_analysis.coverage.title')}
                                </h4>
                                <p className="text-sm text-indigo-700 dark:text-indigo-300">
                                    {t('analytics.procedure_analysis.coverage.desc')} <strong>{t('analytics.procedure_analysis.coverage.desc_bold')}</strong>.
                                    <br />
                                    <span className="font-bold text-red-600 dark:text-red-400">{t('analytics.procedure_analysis.coverage.important')}</span> {t('analytics.procedure_analysis.coverage.desc_continued')}
                                </p>
                            </div>
                            <div className="border border-slate-200 dark:border-slate-700 rounded-2xl overflow-hidden shadow-sm overflow-x-auto">
                                <table className="w-full text-sm">
                                    <thead className="bg-slate-50 dark:bg-slate-900 text-slate-500 font-bold text-xs uppercase">
                                        <tr>
                                            <th className="p-4 text-right">{t('analytics.procedure_analysis.coverage.table.material')}</th>
                                            <th className="p-4 text-center">{t('analytics.procedure_analysis.coverage.table.actual_usage')}</th>
                                            <th className="p-4 text-center">{t('analytics.procedure_analysis.coverage.table.pack_size')}</th>
                                            <th className="p-4 text-center bg-indigo-50/50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300">{t('analytics.procedure_analysis.coverage.table.coverage')}</th>
                                            <th className="p-4 text-center">{t('analytics.procedure_analysis.coverage.table.pack_cost')}</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800 bg-white dark:bg-slate-800">
                                        {(analysis.breakdown || []).map((item, idx) => (
                                            <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-slate-700/50 transition">
                                                <td className="p-4 font-bold text-slate-700 dark:text-slate-200">{item.material_name}</td>
                                                <td className="p-4 text-center text-slate-500 dark:text-slate-400" dir="ltr">
                                                    {item.actual_usage > 0 ? (
                                                        <span>{item.actual_usage} {item.base_unit}</span>
                                                    ) : (
                                                        <span className="text-amber-500 text-xs italic">{t('analytics.procedure_analysis.coverage.waiting_ai')}</span>
                                                    )}
                                                </td>
                                                <td className="p-4 text-center">
                                                    <div className="flex items-center justify-center gap-2">
                                                        <input
                                                            type="number"
                                                            step="0.1"
                                                            defaultValue={item.pack_size}
                                                            onBlur={async (e) => {
                                                                const newVal = parseFloat(e.target.value);
                                                                if (newVal && newVal !== item.pack_size) {
                                                                    try {
                                                                        await updateMaterial(item.material_id, { packaging_ratio: newVal });
                                                                        loadFinancials(selectedProcedure); // Reload analysis
                                                                    } catch (err) {
                                                                        alert(t('analytics.procedure_analysis.update_fail'));
                                                                    }
                                                                }
                                                            }}
                                                            className="w-16 p-1 text-center border rounded bg-white dark:bg-slate-700 dark:border-slate-600 focus:border-indigo-500 outline-none font-bold"
                                                        />
                                                        <span className="text-xs text-slate-400">{item.base_unit}</span>
                                                    </div>
                                                </td>
                                                <td className={`p-4 text-center font-bold text-lg ${item.coverage_per_pack < 1 ? 'text-amber-600 bg-amber-50 dark:bg-amber-900/20 dark:text-amber-400' : 'text-indigo-600 dark:text-indigo-400 bg-indigo-50/30 dark:bg-indigo-900/20'}`}>
                                                    {isFinite(item.coverage_per_pack) ? (item.coverage_per_pack < 1 ? item.coverage_per_pack.toFixed(1) : Math.floor(item.coverage_per_pack)) : 0} <span className="text-xs font-normal text-slate-400">{t('analytics.procedure_analysis.coverage.patient_unit')}</span>
                                                    {item.coverage_per_pack < 1 && <div className="text-[10px] text-amber-600 dark:text-amber-400 font-normal mt-0.5">{t('analytics.procedure_analysis.coverage.usage_exceeds')}</div>}
                                                </td>
                                                <td className="p-4 text-center text-slate-600 dark:text-slate-300 font-mono">{item.cost_per_pack} {t('analytics.general_analysis.currency')}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}
                </>
            ) : null}
        </div>
    );
};
export default ProcedureCostAnalysis;
