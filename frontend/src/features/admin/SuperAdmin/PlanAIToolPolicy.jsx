import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { api } from '@/api';
export default function PlanAIToolPolicy(props) {
    const [open, setOpen] = useState(false);
    const { i18n } = useTranslation();
    return <div className="mt-3 space-y-2"><button type="button" aria-expanded={open} onClick={() => setOpen(!open)} className="font-bold text-sky-700 dark:text-sky-300">{i18n.language.startsWith('ar') ? 'أدوات AI المسموحة للباقة' : 'Allowed AI tools for this plan'}</button>{open && <ToolPicker {...props} />}</div>;
}
function ToolPicker({ value, onChange }) {
    const { i18n } = useTranslation();
    const ar = i18n.language.startsWith('ar');
    const query = useQuery({ queryKey: ['commercial-ai-tools'], queryFn: async () => { const res = await api.get('/api/v1/ai/tools'); return res.data?.data ?? res.data; } });
    let selected = [], malformed = false;
    try {
        const parsed = value == null ? null : JSON.parse(value);
        if (Array.isArray(parsed)) selected = parsed;
        else if (parsed && typeof parsed === 'object') selected = Object.keys(parsed).filter((key) => parsed[key] === true);
        else if (parsed !== null) malformed = true;
    } catch { malformed = true; }
    return <div className="space-y-2 text-sm">
        <p>{ar ? 'توريث المجموعة الحالية لا يمنح صلاحيات المستخدم أو يتجاوز قيود الاشتراك.' : 'Inheriting the current tool set never grants user permissions or bypasses subscription restrictions.'}</p>
        <label className="block"><input type="checkbox" checked={value == null} onChange={(e) => onChange(e.target.checked ? null : '[]')} /> {ar ? 'توريث مجموعة الأدوات الحالية' : 'Inherit the current tool set'}</label>
        {malformed && <p role="alert">{ar ? 'السياسة المحفوظة غير صالحة؛ الأدوات محجوبة حتى تصحيحها.' : 'Saved policy is invalid; tools are denied until corrected.'}</p>}
        {query.isError && <button onClick={() => query.refetch()}>{ar ? 'تعذّر تحميل الأدوات؛ إعادة المحاولة' : 'Tools unavailable; retry'}</button>}
        {query.isPending && <p role="status">{ar ? 'جارٍ تحميل الأدوات…' : 'Loading tools…'}</p>}
        {value != null && !query.isError && (query.data || []).map((tool) => <label key={tool.name} className="block"><input type="checkbox" checked={selected.includes(tool.name)} onChange={(e) => onChange(JSON.stringify(e.target.checked ? [...new Set([...selected, tool.name])] : selected.filter((name) => name !== tool.name)))} /> {tool.description || tool.name}</label>)}
    </div>;
}
