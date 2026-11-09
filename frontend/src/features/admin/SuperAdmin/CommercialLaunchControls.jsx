import CatalogSetupControl from './CatalogSetupControl';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { api } from '@/api';
import { ConfirmDialog } from '@/shared/ui';
import { KNOWN_PLAN_FEATURES } from './planFeatureUtils';

const base = '/api/v1/admin/subscriptions';
const unwrap = (response) => response.data?.data ?? response.data;
const field = 'w-full rounded-lg border border-slate-300 bg-white p-2 text-slate-900 dark:border-slate-600 dark:bg-slate-900 dark:text-white';
const button = 'rounded-lg bg-sky-700 px-4 py-2 font-bold text-white disabled:opacity-50';

export default function CommercialLaunchControls({ onCatalogApplied }) {
    return <div className="space-y-6"><CatalogSetupControl onApplied={onCatalogApplied} /><CommercialPolicyControls /></div>;
}

function CommercialPolicyControls() {
    const { i18n } = useTranslation();
    const ar = i18n.language.startsWith('ar');
    const text = (arabic, english) => ar ? arabic : english;
    const cache = useQueryClient();
    const query = useQuery({ queryKey: ['commercial-launch-controls'], queryFn: async () => {
        const responses = await Promise.all([
            api.get(`${base}/trial-policy`), api.get(`${base}/catalog-inventory`),
            api.get(`${base}/reconciliation-preview`), api.get('/api/v1/admin/features/emergency-restrictions'),
        ]);
        return { trial: unwrap(responses[0]), inventory: unwrap(responses[1]), preview: unwrap(responses[2]), emergency: unwrap(responses[3]) };
    } });
    const [trialPlan, setTrialPlan] = useState('');
    const [days, setDays] = useState('');
    const [capability, setCapability] = useState('ai_insights');
    const [restrict, setRestrict] = useState(true);
    const [reason, setReason] = useState('');
    const [mappings, setMappings] = useState({});
    const [pending, setPending] = useState(null);
    const mutation = useMutation({ mutationFn: async (action) => {
        if (action.kind === 'trial') return api.put(`${base}/trial-policy`, action.payload);
        if (action.kind === 'emergency') return api.post('/api/v1/admin/features/emergency-restrictions', action.payload);
        return api.post(`${base}/reconcile-tenants`, action.payload);
    }, onSuccess: async () => {
        setPending(null); setReason(''); setMappings({});
        await cache.invalidateQueries({ queryKey: ['commercial-launch-controls'] });
        await cache.invalidateQueries({ queryKey: ['tenant-commercial-overrides'] });
    }, onError: () => { setPending(null); } });
    if (query.isPending) return <p role="status">{text('جارٍ تحميل السياسة التجارية…', 'Loading commercial policy…')}</p>;
    if (query.isError) return <div role="alert"><p>{text('تعذّر تحميل السياسة؛ التعديل غير متاح.', 'Policy unavailable; changes are disabled.')}</p><button className={button} onClick={() => query.refetch()}>{text('إعادة المحاولة', 'Retry')}</button></div>;
    const { trial, inventory, preview, emergency } = query.data;
    const plans = inventory.catalog_plans || [];
    const selected = (preview.unanchored_tenants || []).filter((row) => mappings[row.tenant_id]).map((row) => ({
        tenant_id: row.tenant_id, plan_id: Number(mappings[row.tenant_id]),
        expected_revision: row.policy_revision, expected_plan_id: row.current_plan_id ?? null,
    }));
    const ready = reason.trim().length >= 5 && !mutation.isPending;
    const prepare = (kind, payload, description) => setPending({ kind, payload: { ...payload, reason: reason.trim() }, description });
    return <section className="space-y-6 rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-800" dir={ar ? 'rtl' : 'ltr'}>
        <h2 className="text-xl font-bold">{text('الضوابط التجارية', 'Commercial controls')}</h2>
        <p>{text('وضع التنفيذ الحالي', 'Current enforcement mode')}: <strong>{inventory.enforcement_mode}</strong></p>
        {inventory.enforcement_mode !== 'enforce' && <p role="alert">{text('الضوابط التجارية ليست في وضع الإلزام. لا تعتبر هذه البيئة جاهزة للبيع.', 'Commercial enforcement is not enabled. This environment is not ready for paid launch.')}</p>}
        {mutation.isError && <p role="alert">{text('لم يُحفظ التغيير. راجع السبب وحدّث المعاينة عند تعارض النسخة.', 'Change was not saved. Review the reason and refresh after a revision conflict.')} {String(mutation.error?.response?.data?.detail || mutation.error?.message || '')}</p>}
        <label className="block">{text('سبب التغيير', 'Reason for change')}<input className={field} value={reason} maxLength={500} onChange={(e) => setReason(e.target.value)} /></label>
        <div className="space-y-3 border-t pt-4">
            <h3 className="font-bold">{text('تجربة التسجيلات الجديدة', 'Trial for future signups')}</h3>
            <p>{text('الحالي', 'Current')}: {trial.trial_plan_name} · {trial.trial_duration_days} {text('يوم، بدون بطاقة. التجارب القائمة لا تتغير.', 'days, no card. Existing trials are preserved.')}</p>
            <label className="block">{text('باقة التجربة', 'Trial plan')}<select className={field} value={trialPlan || trial.trial_plan_name} onChange={(e) => setTrialPlan(e.target.value)}>{(trial.eligible_plans || []).map((p) => <option key={p.id} value={p.name}>{ar ? p.display_name_ar : p.name}</option>)}</select></label>
            <label className="block">{text('أيام التجربة', 'Trial days')}<input type="number" min={1} max={90} className={field} value={days || trial.trial_duration_days} onChange={(e) => setDays(e.target.value)} /></label>
            <button className={button} disabled={!ready || !(trial.eligible_plans || []).some(p => p.name === (trialPlan || trial.trial_plan_name))} onClick={() => prepare('trial', { trial_plan_name: trialPlan || trial.trial_plan_name, trial_duration_days: Number(days || trial.trial_duration_days), expected_trial_plan_id: trial.trial_plan_id, expected_trial_duration_days: trial.trial_duration_days }, text('تطبيق سياسة التجربة على التسجيلات الجديدة فقط', 'Apply trial policy to future signups only'))}>{text('معاينة سياسة التجربة', 'Preview trial policy')}</button>
        </div>
        <div className="space-y-3 border-t pt-4">
            <h3 className="font-bold">{text('قيود الطوارئ للخصائص', 'Emergency capability restrictions')}</h3>
            <p>{text('تمنع الاستخدام الجديد حتى مع سماح الباقة أو استثناء العيادة. السجلات السريرية السابقة محفوظة.', 'Blocks new affected operations even with a plan or clinic allowance. Existing clinical history is preserved.')}</p>
            <p>{text('القيود الحالية', 'Current restrictions')}: {(emergency.active_restrictions || []).join(', ') || text('لا يوجد', 'None')}</p>
            <label className="block">{text('الخاصية', 'Capability')}<select className={field} value={capability} onChange={(e) => setCapability(e.target.value)}>{KNOWN_PLAN_FEATURES.filter((p) => p.isSellable).map((p) => <option key={p.key} value={p.key}>{ar ? p.label_ar : p.label_en}</option>)}</select></label>
            <label className="block">{text('الإجراء', 'Action')}<select className={field} value={String(restrict)} onChange={(e) => setRestrict(e.target.value === 'true')}><option value="true">{text('تقييد الاستخدام الجديد', 'Restrict new use')}</option><option value="false">{text('رفع قيد الطوارئ', 'Lift emergency restriction')}</option></select></label>
            <button className={button} disabled={!ready} onClick={() => prepare('emergency', { capability_key: capability, is_restricted: restrict, expected_restricted: (emergency.active_restrictions || []).includes(capability) }, `${capability}: ${restrict ? text('تقييد', 'restrict') : text('رفع القيد', 'lift restriction')}`)}>{text('معاينة قيد الطوارئ', 'Preview emergency restriction')}</button>
        </div>
        <div className="space-y-3 border-t pt-4">
            <h3 className="font-bold">{text('الكتالوج ومطابقة العقود القديمة', 'Catalog and legacy contract reconciliation')}</h3>
            <button className={button} disabled={query.isFetching || mutation.isPending} onClick={() => { setMappings({}); query.refetch(); }}>{text('تحديث المعاينة', 'Refresh preview')}</button>
            <div className="overflow-x-auto"><table className="w-full text-start text-sm"><thead><tr>{[text('الباقة', 'Plan'), text('السعر / شهر تقويمي', 'Price / calendar month'), text('الحسابات', 'Accounts'), text('AI / يوم', 'AI / day'), text('متاحة للبيع', 'For sale')].map((title) => <th key={title} className="p-2 text-start">{title}</th>)}</tr></thead><tbody>{plans.map((p) => <tr key={p.id}><td className="p-2">{ar ? p.display_name_ar : p.name} (#{p.id})</td><td>{p.price} EGP</td><td>{p.max_users ?? '—'}</td><td>{p.ai_daily_limit ?? '—'}</td><td>{p.is_active ? text('نعم', 'Yes') : text('متقاعدة', 'Retired')}</td></tr>)}</tbody></table></div>
            {(inventory.warnings || []).map((warning) => <p key={warning} role="alert">{warning}</p>)}
            <p>{text('لا يُحوّل أي عقد تلقائيًا. اختر العيادات والباقة المقصودة صراحةً؛ العقود المرتبطة الصحيحة مستثناة.', 'No automatic mapping. Explicitly select clinics and destination plans; valid existing contracts are excluded.')}</p>
            {(preview.unanchored_tenants || []).map((row) => <label key={row.tenant_id} className="block">{row.tenant_name} (#{row.tenant_id}) · {row.current_raw_plan || '—'}<select className={field} value={mappings[row.tenant_id] || ''} onChange={(e) => setMappings((old) => ({ ...old, [row.tenant_id]: e.target.value }))}><option value="">{text('بدون تغيير', 'Leave unchanged')}</option>{plans.filter((p) => p.is_active).map((p) => <option key={p.id} value={p.id}>{ar ? p.display_name_ar : p.name}</option>)}</select></label>)}
            <button className={button} disabled={!ready || !selected.length || selected.some((m) => !m.expected_revision)} onClick={() => prepare('reconcile', { mappings: selected }, selected.map((m) => `#${m.tenant_id} → #${m.plan_id}`).join(', '))}>{text('معاينة المطابقة المختارة', 'Preview selected mappings')}</button>
        </div>
        <ConfirmDialog isOpen={Boolean(pending)} onClose={() => !mutation.isPending && setPending(null)} onConfirm={() => mutation.mutate(pending)} title={text('تأكيد التغيير التجاري', 'Confirm commercial change')} message={`${pending?.description || ''} · ${pending?.payload?.reason || ''}`} confirmText={text('تأكيد وحفظ', 'Confirm and save')} cancelText={text('إلغاء', 'Cancel')} isLoading={mutation.isPending} />
    </section>;
}
