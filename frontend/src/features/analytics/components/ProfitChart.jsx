import { useTranslation } from 'react-i18next';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

const ProfitChart = ({ data }) => {
    const { t } = useTranslation();

    if (!data) return null;

    const costData = [
        { name: t('analytics.chart.expenses'), value: data.breakdown.expenses },
        { name: t('analytics.chart.materials'), value: data.breakdown.material_costs },
        { name: t('analytics.chart.labs'), value: data.breakdown.lab_costs },
    ].filter(d => d.value > 0);

    const COLORS = ['#F97316', '#F43F5E', '#EC4899']; // Orange, Rose, Pink

    // Custom Tooltip
    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
            return (
                <div className="bg-white/90 backdrop-blur-md p-3 rounded-lg shadow-lg border border-slate-100 text-xs">
                    <p className="font-bold text-slate-800">{payload[0].name}</p>
                    <p className="text-slate-600">
                        ${(payload[0].value || 0).toLocaleString()}
                        <span className="text-slate-400 mx-1">
                            ({((payload[0].value / (data.total_costs || 1)) * 100).toFixed(1)}%)
                        </span>
                    </p>
                </div>
            );
        }
        return null;
    };

    return (
        <div className="bg-surface p-6 rounded-2xl border border-border/50 shadow-sm h-full flex flex-col justify-between">
            <div>
                <h3 className="text-lg font-bold text-text-primary mb-1">{t('analytics.chart.title')}</h3>
                <p className="text-xs text-text-secondary mb-4">{t('analytics.chart.subtitle')}</p>
            </div>

            <div className="h-[250px] relative">
                {costData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                            <Pie
                                data={costData}
                                cx="50%"
                                cy="50%"
                                innerRadius={60}
                                outerRadius={80}
                                paddingAngle={5}
                                dataKey="value"
                                stroke="none"
                            >
                                {costData.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                ))}
                            </Pie>
                            <Tooltip content={<CustomTooltip />} />
                            <Legend
                                verticalAlign="bottom"
                                height={36}
                                iconType="circle"
                                wrapperStyle={{ fontSize: '12px', paddingTop: '20px' }}
                            />
                        </PieChart>
                    </ResponsiveContainer>
                ) : (
                    <div className="flex items-center justify-center h-full text-slate-300">
                        {t('analytics.chart.no_data')}
                    </div>
                )}

                {/* Center Label */}
                {costData.length > 0 && (
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 -mt-4 text-center pointer-events-none">
                        <p className="text-[10px] text-slate-400">{t('analytics.chart.total')}</p>
                        <p className="text-sm font-bold text-slate-700">${data.total_costs > 1000 ? (data.total_costs / 1000).toFixed(1) + 'k' : data.total_costs}</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ProfitChart;