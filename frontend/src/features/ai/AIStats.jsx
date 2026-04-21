import { useState, useEffect } from 'react';
import { api } from '@/api';
import {
    Activity, CheckCircle, XCircle, Clock,
    MessageSquare, AlertTriangle, Search, Filter, Eye,
    Brain, Settings, BarChart2, Shield, FileText, ChevronRight, ChevronLeft
} from 'lucide-react';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
    PieChart, Pie, Cell
} from 'recharts';
// --- Components ---
// 1. Overview Tab
const OverviewTab = ({ stats, costs, suggestions }) => {
    return (
        <div className="space-y-6 animate-fade-in">
            {/* ROI Card */}
            <div className="bg-gradient-to-r from-teal-600 to-emerald-700 rounded-3xl p-8 text-white shadow-xl relative overflow-hidden">
                <div className="relative z-10 grid grid-cols-1 md:grid-cols-4 gap-8">
                    <div>
                        <p className="text-teal-100 text-sm font-bold mb-1">إجمالي العائد (توفير)</p>
                        <h3 className="text-4xl font-black">${costs?.roi?.money_saved_usd || 0}</h3>
                        <p className="text-xs text-teal-200 mt-2">بناءً على {costs?.roi?.hours_saved || 0} ساعة عمل تم توفيرها</p>
                    </div>
                    <div>
                        <p className="text-teal-100 text-sm font-bold mb-1">تكلفة الذكاء الاصطناعي</p>
                        <h3 className="text-4xl font-black text-white/90">${costs?.estimated_cost_usd || 0}</h3>
                        <p className="text-xs text-teal-200 mt-2">{costs?.total_tokens?.toLocaleString() || 0} توكن</p>
                    </div>
                    <div>
                        <p className="text-teal-100 text-sm font-bold mb-1">صافي الفائدة</p>
                        <h3 className="text-4xl font-black text-emerald-300">
                            ${costs?.roi?.net_benefit_usd || 0}
                        </h3>
                        <p className="text-xs text-teal-200 mt-2">القيمة المضافة الحقيقية</p>
                    </div>
                    <div className="flex flex-col justify-center items-end">
                        <div className="bg-white/20 p-4 rounded-2xl backdrop-blur-sm text-center min-w-[120px]">
                            <p className="text-xs font-bold mb-1 text-white/80">الاقتراحات</p>
                            <h3 className="text-3xl font-black text-amber-300 animate-pulse">{suggestions?.length || 0}</h3>
                        </div>
                    </div>
                </div>
                {/* Decoration */}
                <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -mr-16 -mt-16 blur-2xl"></div>
                <div className="absolute bottom-0 left-0 w-48 h-48 bg-teal-500/30 rounded-full -ml-10 -mb-10 blur-xl"></div>
            </div>
            {/* KPI Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <KPICard title="إجمالي الطلبات" value={stats?.total_requests} icon={MessageSquare} color="blue" suffix="طلب" />
                <KPICard title="نسبة النجاح" value={stats?.success_rate} icon={CheckCircle} color="emerald" suffix="%" />
                <KPICard title="متوسط التأخير" value={stats?.avg_latency_ms} icon={Clock} color="amber" suffix="ms" />
                <KPICard title="التوكنز المستهلكة" value={stats?.total_tokens?.toLocaleString()} icon={Activity} color="teal" suffix="T" />
            </div>
            {/* Suggestions Panel */}
            {suggestions?.length > 0 && (
                <div className="bg-amber-50 dark:bg-amber-900/10 border border-amber-100 dark:border-amber-800 p-6 rounded-3xl">
                    <h3 className="font-bold text-lg mb-4 flex items-center gap-2 text-amber-600 dark:text-amber-400">
                        <AlertTriangle size={20} />
                        اقتراحات تحسين الذكاء الاصطناعي
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {suggestions.map((sug, idx) => (
                            <div key={idx} className="bg-white dark:bg-slate-900 p-5 rounded-2xl shadow-sm border-l-4 border-l-amber-400">
                                <span className={`text-[10px] font-black px-2 py-1 rounded uppercase mb-2 inline-block ${sug.type === 'CRITICAL' ? 'bg-red-100 text-red-600' :
                                    sug.type === 'WARNING' ? 'bg-amber-100 text-amber-600' : 'bg-blue-100 text-blue-600'
                                    }`}>
                                    {sug.type === 'CRITICAL' ? 'حرج' : sug.type === 'WARNING' ? 'تحذير' : 'معلومة'}
                                </span>
                                <h4 className="font-bold text-slate-800 dark:text-white mb-1">{sug.message}</h4>
                                <p className="text-sm text-slate-500 mb-3">{sug.action}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};
// 2. Analytics Tab (Failures & Heatmap)
const AnalyticsTab = ({ failures, heatmap, intents }) => {
    return (
        <div className="space-y-6 animate-fade-in">
            {/* Failure Analysis */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 bg-slate-50 dark:bg-slate-950 p-6 rounded-3xl border border-slate-200 dark:border-slate-800">
                {/* Failure Breakdown */}
                <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl shadow-sm">
                    <h3 className="font-bold text-lg mb-4 flex items-center gap-2 text-red-500">
                        <AlertTriangle size={18} />
                        تحليل الأخطاء
                    </h3>
                    <div className="space-y-4">
                        {failures?.by_type?.length > 0 ? (
                            failures.by_type.map((err, idx) => (
                                <div key={idx} className="flex items-center justify-between">
                                    <span className="text-sm font-bold text-slate-600 dark:text-slate-400">{err.type}</span>
                                    <div className="flex items-center gap-2 w-1/2">
                                        <div className="h-2 bg-red-100 rounded-full flex-1 overflow-hidden">
                                            <div className="h-full bg-red-500 rounded-full" style={{ width: `${Math.min(err.count * 10, 100)}%` }}></div>
                                        </div>
                                        <span className="text-xs font-bold text-slate-800 dark:text-white w-8 text-left">{err.count}</span>
                                    </div>
                                </div>
                            ))
                        ) : (
                            <p className="text-slate-400 text-sm text-center py-4">النظام يعمل بكفاءة ✅ لا توجد أخطاء.</p>
                        )}
                    </div>
                </div>
                {/* Confidence Heatmap */}
                <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl shadow-sm">
                    <h3 className="font-bold text-lg mb-4 flex items-center gap-2 text-teal-500">
                        <Activity size={18} />
                        خريطة الثقة
                    </h3>
                    <div className="overflow-x-auto">
                        <table className="w-full text-center text-xs">
                            <thead className="text-slate-400 font-bold border-b border-slate-100 dark:border-slate-800">
                                <tr>
                                    <th className="pb-2 text-right">النية (Intent)</th>
                                    <th className="pb-2 text-red-500">منخفض</th>
                                    <th className="pb-2 text-amber-500">متوسط</th>
                                    <th className="pb-2 text-emerald-500">عالي</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-50 dark:divide-slate-800">
                                {heatmap.map((row, idx) => (
                                    <tr key={idx}>
                                        <td className="py-3 text-right font-bold text-slate-700 dark:text-slate-300">{row.intent}</td>
                                        <td className="py-3"><span className={`px-2 py-1 rounded-lg font-bold ${row.low > 0 ? 'bg-red-100 text-red-600' : 'text-slate-300'}`}>{row.low}</span></td>
                                        <td className="py-3"><span className={`px-2 py-1 rounded-lg font-bold ${row.medium > 0 ? 'bg-amber-100 text-amber-600' : 'text-slate-300'}`}>{row.medium}</span></td>
                                        <td className="py-3"><span className={`px-2 py-1 rounded-lg font-bold ${row.high > 0 ? 'bg-emerald-100 text-emerald-600' : 'text-slate-300'}`}>{row.high}</span></td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            {/* Top Intents */}
            <div className="bg-white dark:bg-slate-900 rounded-3xl p-6 shadow-sm border border-slate-100 dark:border-slate-800">
                <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
                    <Filter size={18} />
                    أداء النوايا الأكثر استخداماً
                </h3>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-right">
                        <thead className="text-slate-400 font-medium border-b border-slate-100 dark:border-slate-800">
                            <tr>
                                <th className="pb-3">النية / الأداة</th>
                                <th className="pb-3">الاستخدام</th>
                                <th className="pb-3">نسبة الفشل</th>
                                <th className="pb-3">متوسط التأخير</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-50 dark:divide-slate-800">
                            {intents.map((intent, idx) => (
                                <tr key={idx} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                                    <td className="py-3 font-semibold text-slate-700 dark:text-slate-300 ltr">{intent.intent}</td>
                                    <td className="py-3">{intent.usage}</td>
                                    <td className={`py-3 font-bold ${intent.failure_rate > 5 ? 'text-red-500' : 'text-emerald-500'}`}>{intent.failure_rate}%</td>
                                    <td className="py-3 text-slate-500">{intent.avg_latency}ms</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
// 3. Logs Tab
const LogsTab = ({ logs, page, setPage, fetchLogDetails, selectedLog, setSelectedLog }) => {
    return (
        <div className="space-y-6 animate-fade-in relative">
            <div className="bg-white dark:bg-slate-900 rounded-3xl p-6 shadow-sm border border-slate-100 dark:border-slate-800">
                <div className="flex justify-between items-center mb-6">
                    <h3 className="font-bold text-lg flex items-center gap-2">
                        <Search size={18} />
                        مستكشف السجلات المباشر
                    </h3>
                    <div className="flex gap-2">
                        <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page === 1} className="p-2 bg-slate-100 rounded-lg hover:bg-slate-200 disabled:opacity-50"><ChevronRight size={16} /></button>
                        <span className="px-4 py-2 bg-slate-50 rounded-lg font-bold text-slate-600">{page}</span>
                        <button onClick={() => setPage(page + 1)} className="p-2 bg-slate-100 rounded-lg hover:bg-slate-200"><ChevronLeft size={16} /></button>
                    </div>
                </div>
                <div className="space-y-3">
                    {logs.map(log => (
                        <div key={log.id} className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-800/50 rounded-2xl border border-slate-100 dark:border-slate-800 hover:border-teal-200 transition-colors cursor-pointer" onClick={() => fetchLogDetails(log.id)}>
                            <div className="flex items-center gap-4">
                                <div className={`p-3 rounded-full ${log.status === 'SUCCESS' ? 'bg-emerald-100 text-emerald-600' : 'bg-red-100 text-red-600'}`}>
                                    {log.status === 'SUCCESS' ? <CheckCircle size={18} /> : <XCircle size={18} />}
                                </div>
                                <div>
                                    <p className="font-bold text-slate-700 dark:text-slate-300">{log.tool || "Chat"}</p>
                                    <div className="flex gap-2 text-xs text-slate-400 font-mono mt-1">
                                        <span>{log.trace_id.substring(0, 8)}...</span>
                                        <span>•</span>
                                        <span>{new Date(log.timestamp).toLocaleTimeString()}</span>
                                    </div>
                                </div>
                            </div>
                            <div className="flex items-center gap-4">
                                <span className="text-xs font-bold text-slate-500 bg-white px-2 py-1 rounded-lg border border-slate-200">{log.latency}ms</span>
                                <ChevronLeft className="text-slate-300" size={16} />
                            </div>
                        </div>
                    ))}
                    {logs.length === 0 && <p className="text-center text-slate-400 py-10">لا توجد سجلات.</p>}
                </div>
            </div>
            {/* Log Detail Modal */}
            {selectedLog && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md p-4 animate-fade-in" style={{ direction: 'rtl' }}>
                    <div className="bg-white dark:bg-slate-900 rounded-3xl p-8 w-full max-w-4xl shadow-2xl h-[85vh] flex flex-col border border-slate-200 dark:border-slate-700">
                        <div className="flex justify-between items-center mb-6">
                            <div>
                                <h3 className="text-xl font-bold flex items-center gap-2">
                                    <Search className="text-teal-500" />
                                    تفاصيل العملية
                                </h3>
                                <p className="font-mono text-sm text-slate-500 mt-1">{selectedLog.trace_id}</p>
                            </div>
                            <button onClick={() => setSelectedLog(null)} className="p-2 hover:bg-red-50 text-slate-400 hover:text-red-500 rounded-full transition-colors">
                                <XCircle size={28} />
                            </button>
                        </div>
                        <div className="flex-1 overflow-y-auto grid grid-cols-2 gap-6 content-start pr-2">
                            <div className="bg-slate-50 dark:bg-slate-800 p-5 rounded-2xl border border-slate-100">
                                <label className="block text-xs font-black text-slate-400 uppercase mb-3 tracking-wider">مدخلات المستخدم</label>
                                <p className="text-sm font-medium text-slate-700 dark:text-slate-300 whitespace-pre-wrap leading-relaxed">{selectedLog.input_text || "لا توجد نصوص (تسجيل صوتي أو أمر نظام)"}</p>
                            </div>
                            <div className="bg-teal-50 dark:bg-teal-900/20 p-5 rounded-2xl border border-teal-100">
                                <label className="block text-xs font-black text-teal-400 uppercase mb-3 tracking-wider">رد الذكاء الاصطناعي</label>
                                <p className="text-sm font-medium text-slate-700 dark:text-slate-300 whitespace-pre-wrap leading-relaxed">{selectedLog.output_text}</p>
                            </div>
                            <div className="col-span-2">
                                <label className="block text-xs font-black text-slate-400 uppercase mb-3 tracking-wider">معاملات الأداة</label>
                                <pre className="bg-slate-900 text-emerald-400 p-5 rounded-2xl text-xs font-mono overflow-x-auto ltr border border-slate-800 shadow-inner">
                                    {tryFormatJSON(selectedLog.tool_params)}
                                </pre>
                            </div>
                            <div className="col-span-2">
                                <label className="block text-xs font-black text-slate-400 uppercase mb-3 tracking-wider">نتائج التنفيذ</label>
                                <pre className="bg-slate-900 text-blue-400 p-5 rounded-2xl text-xs font-mono overflow-x-auto ltr border border-slate-800 shadow-inner">
                                    {tryFormatJSON(selectedLog.tool_result)}
                                </pre>
                            </div>
                            {selectedLog.error_details && (
                                <div className="col-span-2 bg-red-50 dark:bg-red-900/20 p-5 rounded-2xl border border-red-100 dark:border-red-800">
                                    <label className="block text-xs font-black text-red-500 uppercase mb-3 tracking-wider">تفاصيل الخطأ</label>
                                    <pre className="text-red-600 dark:text-red-400 text-xs font-mono whitespace-pre-wrap ltr">
                                        {selectedLog.error_details}
                                    </pre>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
// 4. Governance Tab
const GovernanceTab = ({ governance, updateGovernance, saving }) => {
    return (
        <div className="space-y-6 animate-fade-in">
            <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 p-8 rounded-3xl shadow-sm">
                <div className="flex justify-between items-center mb-8">
                    <h3 className="font-bold text-xl flex items-center gap-3 text-slate-800 dark:text-white">
                        <Shield className="text-emerald-500" size={24} />
                        الحوكمة وبروتوكولات الأمان
                    </h3>
                    {saving && <span className="text-sm text-emerald-500 animate-pulse font-bold bg-emerald-50 px-3 py-1 rounded-full">جاري حفظ التغييرات...</span>}
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                    <div className="space-y-8">
                        <ToggleSetting
                            label="حجب البيانات الحساسة (PII Masking)"
                            desc="تشفير الأسماء والمعرفات تلقائياً في السجلات."
                            enabled={governance?.ai_sensitive_masking}
                            onToggle={(val) => updateGovernance('ai_sensitive_masking', val)}
                        />
                        <div className="h-px bg-slate-100"></div>
                        <ToggleSetting
                            label="حظر تلقائي عند الفشل"
                            desc="تعطيل الأدوات التي تتجاوز نسبة فشلها 50% لمنع الأخطاء المتكررة."
                            enabled={governance?.ai_auto_block_failure}
                            onToggle={(val) => updateGovernance('ai_auto_block_failure', val)}
                        />
                        <div className="h-px bg-slate-100"></div>
                        <ToggleSetting
                            label="مراجعة بشرية مطلوبة"
                            desc="طلب موافقة الأدمن للإجراءات الخطرة (مثل الحذف أو الدفع)."
                            enabled={governance?.ai_require_human_review}
                            onToggle={(val) => updateGovernance('ai_require_human_review', val)}
                        />
                    </div>
                    <div className="bg-slate-50 dark:bg-slate-800 p-8 rounded-3xl flex flex-col justify-center border border-slate-200 dark:border-slate-700">
                        <label className="text-sm font-bold text-slate-500 mb-4 uppercase tracking-wider">حد الإنفاق اليومي</label>
                        <div className="flex items-end gap-2 mb-2">
                            <div className="flex-1 relative">
                                <span className="absolute left-0 bottom-2 text-2xl font-black text-slate-300">$</span>
                                <input
                                    type="number"
                                    step="0.1"
                                    defaultValue={governance?.ai_max_daily_cost}
                                    onBlur={(e) => updateGovernance('ai_max_daily_cost', e.target.value)}
                                    className="text-5xl font-black bg-transparent border-b-4 border-slate-200 focus:border-teal-500 outline-none w-full pb-2 ltr pl-6 transition-colors"
                                />
                            </div>
                        </div>
                        <p className="text-sm text-slate-400 mt-4 leading-relaxed">
                            سيقوم النظام بإيقاف عمليات الذكاء الاصطناعي تلقائياً عند الوصول لهذا الحد وإشعار الأدمن عبر البريد/SMS.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
// --- Main Page Component ---
const AIStats = () => {
    // State
    const [activeTab, setActiveTab] = useState('overview');
    const [period, setPeriod] = useState("24h");
    const [stats, setStats] = useState(null);
    const [costs, setCosts] = useState(null);
    const [suggestions, setSuggestions] = useState([]);
    const [failures, setFailures] = useState(null);
    const [heatmap, setHeatmap] = useState([]);
    const [intents, setIntents] = useState([]);
    const [logs, setLogs] = useState([]);
    const [governance, setGovernance] = useState(null);
    const [logsPage, setLogsPage] = useState(1);
    const [selectedLog, setSelectedLog] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    // Initial Load
    useEffect(() => {
        fetchAllData();
    }, [period]);
    // Logs Pagination
    useEffect(() => {
        fetchLogs();
    }, [logsPage]);
    const fetchAllData = async () => {
        setLoading(true);
        try {
            await Promise.all([
                fetchDashboard(),
                fetchAnalytics(),
                fetchGovernance(),
                fetchLogs()
            ]);
        } finally {
            setLoading(false);
        }
    };
    const fetchDashboard = async () => {
        try {
            const [s, c, sug] = await Promise.all([
                api.get(`/api/v1/admin/ai/stats?period=${period}`),
                api.get(`/api/v1/admin/ai/costs?period=${period}`),
                api.get('/api/v1/admin/ai/suggestions')
            ]);
            setStats(s.data);
            setCosts(c.data);
            setSuggestions(Array.isArray(sug.data) ? sug.data : []);
        } catch (e) { console.error(e); }
    };
    const fetchAnalytics = async () => {
        try {
            const [f, h, i] = await Promise.all([
                api.get('/api/v1/admin/ai/failures'),
                api.get('/api/v1/admin/ai/heatmap'),
                api.get('/api/v1/admin/ai/intents')
            ]);
            setFailures(f.data || null);
            setHeatmap(Array.isArray(h.data) ? h.data : []);
            setIntents(Array.isArray(i.data) ? i.data : []);
        } catch (e) { console.error(e); }
    };
    const fetchGovernance = async () => {
        try {
            const res = await api.get('/api/v1/admin/ai/governance');
            setGovernance(res.data);
        } catch (e) { console.error(e); }
    };
    const fetchLogs = async () => {
        try {
            const res = await api.get(`/api/v1/admin/ai/logs?page=${logsPage}&limit=15`);
            const logsData = res.data?.data;
            setLogs(Array.isArray(logsData) ? logsData : []);
        } catch (e) { console.error(e); }
    };
    const fetchLogDetails = async (id) => {
        try {
            const res = await api.get(`/api/v1/admin/ai/logs/${id}`);
            setSelectedLog(res.data);
        } catch (e) { alert("فشل تحميل التفاصيل"); }
    };
    const updateGovernance = async (key, value) => {
        if (!governance) return;
        setSaving(true);
        const newSettings = { ...governance, [key]: value };
        setGovernance(newSettings);
        try {
            await api.post('/api/v1/admin/ai/governance', { [key]: value });
        } catch (e) {
            console.error(e);
            alert("فشل التحديث");
            fetchGovernance();
        } finally {
            setSaving(false);
        }
    };
    if (loading && !stats) return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50">
            <div className="flex flex-col items-center gap-4">
                <div className="w-16 h-16 border-4 border-teal-200 border-t-teal-600 rounded-full animate-spin"></div>
                <p className="text-teal-600 font-bold animate-pulse">جاري تهيئة النظام الذكي...</p>
            </div>
        </div>
    );
    return (
        <div className="min-h-screen bg-slate-50/50 pb-20 font-sans" dir="rtl">
            {/* Top Bar */}
            <div className="bg-white sticky top-0 z-30 shadow-sm border-b border-slate-100 px-8 py-4 mb-8">
                <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-gradient-to-br from-teal-500 to-teal-600 rounded-xl shadow-lg shadow-teal-200">
                            <Brain className="text-white" size={24} />
                        </div>
                        <div>
                            <h1 className="text-2xl font-black text-slate-800 tracking-tight">مركز التحكم بالذكاء الاصطناعي</h1>
                            <p className="text-slate-500 text-sm font-medium">الذكاء والحوكمة اللحظية</p>
                        </div>
                    </div>
                    {/* Period Selector */}
                    <div className="flex bg-slate-100 p-1.5 rounded-xl">
                        {["24h", "7d", "30d"].map(p => (
                            <button
                                key={p}
                                onClick={() => setPeriod(p)}
                                className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${period === p
                                    ? 'bg-white text-teal-700 shadow-sm'
                                    : 'text-slate-500 hover:text-slate-700'
                                    }`}
                            >
                                {p === "24h" ? "اليوم" : p === "7d" ? "أسبوع" : "شهر"}
                            </button>
                        ))}
                    </div>
                </div>
            </div>
            <div className="max-w-7xl mx-auto px-8">
                {/* Tabs */}
                <div className="flex items-center gap-2 mb-8 overflow-x-auto pb-2">
                    <TabButton active={activeTab} id="overview" label="نظرة عامة والعائد" icon={BarChart2} onClick={setActiveTab} />
                    <TabButton active={activeTab} id="analytics" label="تحليلات عميقة" icon={Activity} onClick={setActiveTab} />
                    <TabButton active={activeTab} id="logs" label="سجل العمليات" icon={FileText} onClick={setActiveTab} />
                    <TabButton active={activeTab} id="governance" label="الحوكمة والأمان" icon={Shield} onClick={setActiveTab} />
                </div>
                {/* Content */}
                <div className="min-h-[600px]">
                    {activeTab === 'overview' && <OverviewTab stats={stats} costs={costs} suggestions={suggestions} />}
                    {activeTab === 'analytics' && <AnalyticsTab failures={failures} heatmap={heatmap} intents={intents} />}
                    {activeTab === 'logs' && <LogsTab logs={logs} page={logsPage} setPage={setLogsPage} fetchLogDetails={fetchLogDetails} selectedLog={selectedLog} setSelectedLog={setSelectedLog} />}
                    {activeTab === 'governance' && <GovernanceTab governance={governance} updateGovernance={updateGovernance} saving={saving} />}
                </div>
            </div>
        </div>
    );
};
// --- Helpers ---
const TabButton = ({ active, id, label, icon: Icon, onClick }) => (
    <button
        onClick={() => onClick(id)}
        className={`flex items-center gap-2 px-6 py-3 rounded-2xl transition-all duration-300 font-bold text-sm whitespace-nowrap ${active === id
            ? 'bg-teal-600 text-white shadow-lg shadow-teal-200 scale-105'
            : 'bg-white text-slate-500 hover:bg-slate-50 hover:text-slate-700 border border-slate-100'
            }`}
    >
        <Icon size={18} />
        {label}
    </button>
);
const KPICard = ({ title, value, icon: Icon, color, suffix }) => {
    const colors = {
        blue: "bg-blue-50 text-blue-600",
        emerald: "bg-emerald-50 text-emerald-600",
        amber: "bg-amber-50 text-amber-600",
        teal: "bg-teal-50 text-teal-600",
    };
    return (
        <div className="bg-white p-6 rounded-3xl shadow-sm border border-slate-100 flex items-center justify-between group hover:shadow-md transition-all">
            <div>
                <p className="text-slate-400 text-xs font-bold uppercase tracking-wider mb-1">{title}</p>
                <h3 className="text-2xl font-black text-slate-800">
                    {value || 0}<span className="text-sm text-slate-400 font-medium ml-1">{suffix}</span>
                </h3>
            </div>
            <div className={`p-4 rounded-2xl ${colors[color]} group-hover:scale-110 transition-transform`}>
                <Icon size={24} />
            </div>
        </div>
    );
};
function tryFormatJSON(str) {
    try { return JSON.stringify(JSON.parse(str), null, 2); } catch (e) { return str; }
}
const ToggleSetting = ({ label, desc, enabled, onToggle }) => (
    <div className="flex items-center justify-between group">
        <div>
            <h4 className="font-bold text-slate-700 text-sm mb-1 group-hover:text-teal-600 transition-colors">{label}</h4>
            <p className="text-xs text-slate-400 max-w-sm leading-relaxed">{desc}</p>
        </div>
        <button
            onClick={() => onToggle(!enabled)}
            className={`w-14 h-8 rounded-full p-1 transition-all duration-300 focus:outline-none focus:ring-4 focus:ring-teal-100 ${enabled ? 'bg-teal-600' : 'bg-slate-200'}`}
        >
            <div className={`w-6 h-6 rounded-full bg-white shadow-sm transition-all duration-300 ${enabled ? 'translate-x-[24px]' : 'translate-x-0'}`}></div>
        </button>
    </div>
);
export default AIStats;

