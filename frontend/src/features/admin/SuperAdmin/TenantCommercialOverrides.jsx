import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { api } from '@/api';
import { ConfirmDialog } from '@/shared/ui';
import { KNOWN_PLAN_FEATURES } from './planFeatureUtils';

export default function TenantCommercialOverrides(props) {
    const [open, setOpen] = useState(false);
    const { i18n } = useTranslation();
    return <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
        <button type="button" aria-expanded={open} className="font-bold text-sky-700 dark:text-sky-300" onClick={() => setOpen(!open)}>{i18n.language.startsWith('ar') ? 'الاستثناءات التجارية للعيادة' : 'Clinic commercial overrides'}</button>
        {open && <OverrideEditor key={props.tenantId} {...props} />}
    </div>;
}

function OverrideEditor({ tenantId, onSaved }) {
    const { i18n } = useTranslation();
    const ar = i18n.language.startsWith('ar');
    const text = (a, e) => ar ? a : e;
    const cache = useQueryClient();
    const key = ['tenant-commercial-overrides', tenantId];
    const query = useQuery({ queryKey: key, queryFn: async () => {
        const res = await api.get(`/api/v1/admin/tenants/${tenantId}/commercial-overrides`);
        return res.data?.data ?? res.data;
    } });
    const [cap, setCap] = useState('ai_insights');
    const [value, setValue] = useState('inherit');
    const [expires, setExpires] = useState('');
    const [reason, setReason] = useState('');
    const [pending, setPending] = useState(null);
    const mutation = useMutation({ mutationFn: (payload) => api.put(`/api/v1/admin/tenants/${tenantId}/commercial-overrides`, payload), onSuccess: async () => {
        setPending(null); setReason('');
        await cache.invalidateQueries({ queryKey: key });
        await onSaved?.();
    }, onError: () => setPending(null) });
    if (query.isPending) return <p role="status">{text('جارٍ تحميل الاستثناءات…', 'Loading overrides…')}</p>;
    if (query.isError) return <button onClick={() => query.refetch()}>{text('تعذّر التحميل؛ إعادة المحاولة', 'Load failed; retry')}</button>;
    const current = query.data.overrides?.find((o) => o.capability_key === cap);
    const field = 'block w-full rounded border border-slate-300 bg-white p-2 dark:border-slate-600 dark:bg-slate-900';
    return <div className="space-y-3 pt-3" dir={ar ? 'rtl' : 'ltr'}>
        <p>{text('السماح التجاري لا يتجاوز صلاحيات المستخدم أو حالة الاشتراك أو قيد الطوارئ. هذه الاستثناءات منفصلة عن إطلاق الخصائص التجريبي.', 'Commercial allowance never overrides role permissions, subscription state or emergency restrictions. These overrides are separate from pilot rollout.')}</p>
        <label>{text('الخاصية التجارية', 'Commercial capability')}<select className={field} value={cap} onChange={(e) => setCap(e.target.value)}>{KNOWN_PLAN_FEATURES.filter((p) => p.isSellable).map((p) => <option key={p.key} value={p.key}>{ar ? p.label_ar : p.label_en}</option>)}</select></label>
        <p>{text('الإعداد الحالي', 'Configured')}: {current?.override_value || 'inherit'} · {text('النتيجة التجارية', 'Commercial result')}: {String(query.data.effective_capabilities?.[cap] ?? '—')} · {text('المراجعة', 'Revision')}: {query.data.policy_revision}</p>
        {current?.expires_at && <p>{text('ينتهي', 'Expires')}: {current.expires_at} {current.is_expired ? text('(منتهي)', '(expired)') : ''}</p>}
        <label>{text('قيمة الاستثناء', 'Override value')}<select className={field} value={value} onChange={(e) => setValue(e.target.value)}><option value="inherit">{text('توريث الباقة', 'Inherit plan')}</option><option value="allow">{text('سماح تجاري', 'Commercial allow')}</option><option value="deny">{text('منع تجاري', 'Commercial deny')}</option></select></label>
        <label>{text('انتهاء الاستثناء اختياري', 'Optional expiry')}<input className={field} type="datetime-local" value={expires} onChange={(e) => setExpires(e.target.value)} /></label>
        <label>{text('سبب الاستثناء', 'Override reason')}<input className={field} value={reason} maxLength={500} onChange={(e) => setReason(e.target.value)} /></label>
        {mutation.isError && <p role="alert">{text('تعذّر الحفظ. حدّث البيانات عند تعارض المراجعة.', 'Save failed. Refresh after a revision conflict.')} {String(mutation.error?.response?.data?.detail || '')}</p>}
        <button className="rounded bg-sky-700 px-4 py-2 text-white disabled:opacity-50" disabled={reason.trim().length < 5 || mutation.isPending || query.isFetching} onClick={() => setPending({ expected_revision: query.data.policy_revision, reason: reason.trim(), overrides: [{ capability_key: cap, override_value: value, expires_at: expires ? new Date(expires).toISOString() : null }] })}>{text('معاينة الاستثناء', 'Preview override')}</button>
        <button className="ms-3 text-sky-700" onClick={() => query.refetch()}>{text('تحديث', 'Refresh')}</button>
        <ConfirmDialog isOpen={Boolean(pending)} onClose={() => !mutation.isPending && setPending(null)} onConfirm={() => mutation.mutate(pending)} title={text('تأكيد الاستثناء', 'Confirm override')} message={`${cap}: ${value} · ${reason}`} confirmText={text('تأكيد وحفظ', 'Confirm and save')} cancelText={text('إلغاء', 'Cancel')} isLoading={mutation.isPending} />
    </div>;
}
