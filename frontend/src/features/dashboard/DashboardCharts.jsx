import {
    AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
    PieChart, Pie, Cell, Legend,
} from 'recharts';

// Load the complete chart together: Recharts inspects its direct children's
// component types, which React.lazy wrappers around Area/Pie/axes conceal.
export function RevenueChart({ data, formatCurrency, revenueLabel }) {
    return (
        <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 10, right: 8, left: -18, bottom: 0 }}>
                <defs>
                    <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#0891B2" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#0891B2" stopOpacity={0} />
                    </linearGradient>
                </defs>
                <XAxis dataKey="name" interval="preserveStartEnd" axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 9, fontWeight: 700 }} dy={8} minTickGap={18} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 9, fontWeight: 700 }} width={42} />
                <Tooltip
                    contentStyle={{ backgroundColor: 'var(--surface-elevated)', borderRadius: '14px', border: 'none', boxShadow: '0 12px 28px rgba(15,23,42,.16)', padding: '10px' }}
                    itemStyle={{ color: 'var(--text-primary)', fontWeight: '800', fontSize: '12px' }}
                    formatter={value => [formatCurrency(value), revenueLabel]}
                    cursor={{ stroke: '#0891B2', strokeWidth: 2, strokeDasharray: '6 6' }}
                />
                <Area type="monotone" dataKey="revenue" stroke="#0891B2" strokeWidth={3} fillOpacity={1} fill="url(#colorRevenue)" activeDot={{ r: 6, strokeWidth: 0, fill: '#0891B2' }} />
            </AreaChart>
        </ResponsiveContainer>
    );
}

export function StatusChart({ data }) {
    return (
        <ResponsiveContainer width="100%" height="100%">
            <PieChart>
                <Pie data={data} innerRadius="45%" outerRadius="65%" paddingAngle={5} dataKey="value">
                    {data.map(item => <Cell key={item.name} fill={item.fill} />)}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: 'var(--surface-elevated)', color: 'var(--text-primary)', borderRadius: '12px', border: 'none', boxShadow: '0 10px 18px rgba(15,23,42,.12)', fontSize: '12px' }} />
                <Legend wrapperStyle={{ fontSize: '12px' }} />
            </PieChart>
        </ResponsiveContainer>
    );
}
