import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { api } from '@/api';
import { Button, ConfirmDialog } from '@/shared/ui';

const base = '/api/v1/admin/subscriptions';
const unwrap = response => response.data?.data ?? response.data;
export default function CatalogSetupControl({ onApplied }) {
    const { i18n } = useTranslation();
    const text = (ar,en) => i18n.language.startsWith('ar') ? ar : en;
    const cache = useQueryClient();
    const [preview,setPreview] = useState(null);
    const [reason,setReason] = useState('');
    const [error,setError] = useState('');
    const [busy,setBusy] = useState(false);
    const [confirm,setConfirm] = useState(false);
    const [saved,setSaved] = useState(false);
    const load = async () => {
        setBusy(true);setPreview(null);setError('');setSaved(false);
        try { setPreview(unwrap(await api.get(`${base}/catalog-setup-preview`))); }
        catch(err) { setError(String(err.response?.data?.detail || err.message)); }
        finally { setBusy(false); }
    };
    const apply = async () => {
        if (!preview || busy) return;
        setBusy(true);setError('');
        try {
            await api.post(`${base}/catalog-setup`,{expected_snapshot:preview.snapshot,reason:reason.trim()});
            setSaved(true);setPreview(null);
            await cache.invalidateQueries({queryKey:['commercial-launch-controls']});
            await onApplied?.();
        } catch(err) { setPreview(null);setError(String(err.response?.data?.detail || err.message)); }
        finally { setBusy(false);setConfirm(false); }
    };
    return <section className="space-y-3" dir={i18n.language.startsWith('ar')?'rtl':'ltr'}>
        <h3 className="text-type-heading font-bold">{text('تهيئة الباقات المعتمدة والتجربة','Approved catalog and trial setup')}</h3>
        <p>{text('أضف الباقات المفقودة واضبط تجربة التسجيلات الجديدة. اشتراكات العيادات والباقات القديمة تبقى كما هي.','Add missing plans and configure future trials. Existing clinic subscriptions and legacy plans remain unchanged.')}</p>
        <label className="block">{text('سبب التهيئة','Setup reason')}<input className="w-full rounded border p-2" value={reason} maxLength={500} onChange={e=>setReason(e.target.value)}/></label>
        <Button disabled={busy} onClick={load}>{text('معاينة تهيئة الباقات المعتمدة','Preview approved catalog setup')}</Button>
        {error && <p role="alert">{error}</p>}
        {saved && <p role="status">{text('حُفظت التهيئة. حدّث صفحة الخطط لمراجعة الكتالوج.','Setup saved. Refresh the plans page to review the catalog.')}</p>}
        {preview && <div className="space-y-2">
            <h4>{text('باقات ستُضاف','Plans to create')}</h4>
            {preview.create_plans.map(p=><p key={p.name}>{p.name} · {p.price} EGP · {p.max_users} {text('حسابات','accounts')} · {p.ai_daily_limit} AI/{text('يوم','day')}</p>)}
            <h4>{text('باقات قديمة محفوظة دون تغيير','Existing plans preserved without changes')}</h4>
            {preview.preserved_plans.map(p=><p key={p.id}>{p.name} · {p.price} EGP (#{p.id})</p>)}
            <p>{text('التجربة المقترحة: Professional، 14 يومًا، بدون بطاقة، للتسجيلات الجديدة فقط.','Proposed trial: Professional, 14 days, no card, future signups only.')}</p>
            {preview.conflicts.map(p=><p role="alert" key={p.plan_id}>{p.name}: {text('يلزم مراجعة الإعدادات الحالية أولًا','Review existing settings first')} ({p.fields.join(', ')})</p>)}
            <Button disabled={busy || reason.trim().length<5 || preview.conflicts.length>0 || preview.already_configured} onClick={()=>setConfirm(true)}>{text('مراجعة التهيئة وتأكيدها','Review and confirm setup')}</Button>
        </div>}
        <ConfirmDialog isOpen={confirm} onClose={()=>setConfirm(false)} onConfirm={apply} title={text('تأكيد تهيئة الباقات','Confirm catalog setup')} message={text('إنشاء الباقات الناقصة وضبط Professional لمدة 14 يومًا للتجارب الجديدة. لا تتغير اشتراكات العيادات القائمة.','Create missing plans and set Professional/14-day future trials. Existing subscriptions stay unchanged.')} confirmText={text('تأكيد التهيئة','Confirm setup')} isLoading={busy}/>
    </section>;
}
