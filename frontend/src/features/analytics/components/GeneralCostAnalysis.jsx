import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { getAllProceduresFinancials } from '@/api/financials';
import { TrendingDown, TrendingUp, AlertTriangle, DollarSign, Activity, ArrowUpDown } from 'lucide-react';

const GeneralCostAnalysis = () => {
    const { t } = useTranslation();
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [sortConfig, setSortConfig] = useState({ key: 'margin_percent', direction: 'asc' });

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const res = await getAllProceduresFinancials();
            if (Array.isArray(res.data)) {
                setData(res.data);
            } else {
                console.error("GeneralCostAnalysis: API returned non-array", res.data);
                setData([]);
            }
        } catch (err) {
            console.error("Failed to load general analysis", err);
        } finally {
            setLoading(false);
        }
    };

    const handleSort = (key) => {
        let direction = 'asc';
        if (sortConfig.key === key && sortConfig.direction === 'asc') {
            direction = 'desc';
        }
        setSortConfig({ key, direction });
    };

    const isDataArray = Array.isArray(data);

    // Sort logic
    const sortedData = isDataArray ? [...data].sort((a, b) => {
        if (a[sortConfig.key] < b[sortConfig.key]) {
            return sortConfig.direction === 'asc' ? -1 : 1;
        }
        if (a[sortConfig.key] > b[sortConfig.key]) {
            return sortConfig.direction === 'asc' ? 1 : -1;
        }
        return 0;
    }) : [];

    const getMarginColor = (percent) => {
        if (percent < 30) return 'text-red-600 bg-red-50 dark:bg-red-900/20';
        if (percent < 50) return 'text-amber-600 bg-amber-50 dark:bg-amber-900/20';
        return 'text-emerald-600 bg-emerald-50 dark:bg-emerald-900/20';
    };

    const averages = isDataArray && data.length > 0 ? {
        margin: data.reduce((acc, curr) => acc + curr.margin_percent, 0) / data.length,
        cost: data.reduce((acc, curr) => acc + curr.cost, 0) / data.length
    } : { margin: 0, cost: 0 };

    if (loading) return <div className="p-12 text-center text-slate-500 animate-pulse">{t('analytics.general_analysis.loading')}</div>;

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white dark:bg-slate-800 p-4 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm flex items-center gap-4">
                    <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-xl text-blue-600 dark:text-blue-400">
                        <Activity size={24} />
                    </div>
                    <div>
                        <div className="text-sm text-slate-500 font-bold">{t('analytics.general_analysis.total_procedures')}</div>
                        <div className="text-2xl font-black text-slate-800 dark:text-white">{data.length}</div>
                    </div>
                </div>

                <div className="bg-white dark:bg-slate-800 p-4 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm flex items-center gap-4">
                    <div className={`p-3 rounded-xl ${averages.margin < 30 ? 'bg-red-50 text-red-600' : 'bg-emerald-50 text-emerald-600'}`}>
                        {averages.margin < 30 ? <TrendingDown size={24} /> : <TrendingUp size={24} />}
                    </div>
                    <div>
                        <div className="text-sm text-slate-500 font-bold">{t('analytics.general_analysis.avg_margin')}</div>
                        <div className={`text-2xl font-black ${averages.margin < 30 ? 'text-red-600' : 'text-emerald-600'}`}>
                            {averages.margin.toFixed(1)}%
                        </div>
                    </div>
                </div>

                <div className="bg-white dark:bg-slate-800 p-4 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm flex items-center gap-4">
                    <div className="p-3 bg-amber-50 dark:bg-amber-900/20 rounded-xl text-amber-600 dark:text-amber-400">
                        <DollarSign size={24} />
                    </div>
                    <div>
                        <div className="text-sm text-slate-500 font-bold">{t('analytics.general_analysis.avg_cost')}</div>
                        <div className="text-2xl font-black text-slate-800 dark:text-white">{averages.cost.toFixed(0)} <span className="text-xs font-normal text-slate-400">{t('analytics.general_analysis.currency')}</span></div>
                    </div>
                </div>
            </div>

            {/* Analysis Table */}
            <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm overflow-hidden">
                <div className="p-4 border-b border-slate-100 dark:border-slate-700 flex justify-between items-center">
                    <h3 className="font-bold text-slate-800 dark:text-white">{t('analytics.general_analysis.table.title')}</h3>
                    <div className="text-xs text-slate-400">{t('analytics.general_analysis.table.subtitle')}</div>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead className="bg-slate-50 dark:bg-slate-900 text-slate-500 font-bold text-xs uppercase">
                            <tr>
                                <th className="p-4 text-right cursor-pointer hover:text-indigo-600 transition-colors" onClick={() => handleSort('name')}>
                                    <div className="flex items-center gap-1">{t('analytics.general_analysis.table.procedure')} <ArrowUpDown size={12} /></div>
                                </th>
                                <th className="p-4 text-center cursor-pointer hover:text-indigo-600 transition-colors" onClick={() => handleSort('price')}>
                                    <div className="flex items-center justify-center gap-1">{t('analytics.general_analysis.table.price')} <ArrowUpDown size={12} /></div>
                                </th>
                                <th className="p-4 text-center cursor-pointer hover:text-indigo-600 transition-colors" onClick={() => handleSort('cost')}>
                                    <div className="flex items-center justify-center gap-1">{t('analytics.general_analysis.table.cost_ai')} <ArrowUpDown size={12} /></div>
                                </th>
                                <th className="p-4 text-center cursor-pointer hover:text-indigo-600 transition-colors" onClick={() => handleSort('margin_percent')}>
                                    <div className="flex items-center justify-center gap-1">{t('analytics.general_analysis.table.margin')} <ArrowUpDown size={12} /></div>
                                </th>
                                <th className="p-4 text-center">{t('analytics.general_analysis.table.materials_used')}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                            {sortedData.map((item) => (
                                <tr key={item.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
                                    <td className="p-4 font-bold text-slate-700 dark:text-slate-200">{item.name}</td>
                                    <td className="p-4 text-center text-slate-600 dark:text-slate-300">{item.price}</td>
                                    <td className="p-4 text-center font-mono text-slate-600 dark:text-slate-300">{item.cost}</td>
                                    <td className="p-4 text-center">
                                        <span className={`px-2 py-1 rounded-lg text-xs font-bold ${getMarginColor(item.margin_percent)}`}>
                                            {item.margin_percent}%
                                        </span>
                                    </td>
                                    <td className="p-4 text-center text-slate-500">
                                        <div className="flex items-center justify-center gap-1">
                                            {item.materials_count}
                                            <span className="text-[10px] text-slate-300">{t('analytics.general_analysis.table.material_count')}</span>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default GeneralCostAnalysis;
