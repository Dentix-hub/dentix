import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getPatientInvoice } from '../api';

const CURRENCY_LABELS = { EGP: 'ج.م' };

function formatMoney(value) {
    if (value === null || value === undefined) return '0.00';
    return Number(value).toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
}

export default function PrintInvoice() {
    const { id } = useParams();
    const [invoice, setInvoice] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        let cancelled = false;
        async function fetchData() {
            try {
                const res = await getPatientInvoice(id);
                if (cancelled) return;
                setInvoice(res.data);
                // Auto print after small delay
                setTimeout(() => window.print(), 500);
            } catch (err) {
                if (!cancelled) {
                    setError(
                        err?.response?.status === 403
                            ? 'لا تملك صلاحية عرض الفاتورة المالية'
                            : 'تعذر تحميل الفاتورة'
                    );
                }
            }
        }
        fetchData();
        return () => { cancelled = true; };
    }, [id]);

    if (error) return <div className="p-8 text-center text-red-600 font-cairo" dir="rtl">{error}</div>;
    if (!invoice) return <div>Loading...</div>;

    const currencyLabel = CURRENCY_LABELS[invoice.currency] || invoice.currency;
    const { totals } = invoice;

    return (
        <div className="bg-white p-8 min-h-screen font-cairo" dir="rtl">
            {/* Header */}
            <div className="flex justify-between items-end border-b-2 border-slate-800 pb-4 mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900">{invoice.clinic_name}</h1>
                    {invoice.clinic_tagline && <p className="text-slate-600 mt-1">{invoice.clinic_tagline}</p>}
                </div>
                <div className="text-left text-sm text-slate-500">
                    <p>Date: {invoice.data_as_of ? new Date(invoice.data_as_of).toLocaleDateString() : new Date().toLocaleDateString()}</p>
                    <p>Invoice #: {invoice.invoice_number}</p>
                </div>
            </div>
            {/* Patient Info */}
            <div className="mb-8 p-4 bg-slate-50 rounded-lg border border-slate-200">
                <h2 className="text-lg font-bold mb-2">بيانات المريض</h2>
                <div className="grid grid-cols-2 gap-4">
                    <p><span className="text-slate-500">الاسم:</span> <span className="font-bold">{invoice.patient_name}</span></p>
                    <p><span className="text-slate-500">رقم الهاتف:</span> <span dir="ltr" className="font-mono">{invoice.patient_phone || '-'}</span></p>
                </div>
            </div>
            {/* Treatments Table */}
            <div className="mb-8">
                <table className="w-full text-right border-collapse">
                    <thead>
                        <tr className="border-b border-slate-300">
                            <th className="py-2 text-slate-600">الإجراء العلاجي</th>
                            <th className="py-2 text-slate-600 w-32">التاريخ</th>
                            <th className="py-2 text-slate-600 w-24">التكلفة</th>
                            <th className="py-2 text-slate-600 w-24">الخصم</th>
                            <th className="py-2 text-slate-600 w-28">الصافي</th>
                        </tr>
                    </thead>
                    <tbody>
                        {invoice.line_items.map((item) => (
                            <tr key={item.id} className="border-b border-slate-100">
                                <td className="py-3 font-bold text-slate-800">{item.diagnosis} - {item.procedure} <span className="text-xs text-slate-500">({item.tooth_number || 'عام'})</span></td>
                                <td className="py-3 text-slate-600">{item.date ? new Date(item.date).toLocaleDateString() : '-'}</td>
                                <td className="py-3 font-mono">{formatMoney(item.cost)}</td>
                                <td className="py-3 font-mono">{formatMoney(item.discount)}</td>
                                <td className="py-3 font-mono font-bold">{formatMoney(item.net_amount)}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            {/* Totals */}
            <div className="flex justify-end">
                <div className="w-64 space-y-2">
                    <div className="flex justify-between py-2 border-b border-slate-100">
                        <span className="text-slate-600">الإجمالي</span>
                        <span className="font-bold text-lg">{formatMoney(totals.gross_total)} {currencyLabel}</span>
                    </div>
                    <div className="flex justify-between py-2 border-b border-slate-100">
                        <span className="text-slate-600">إجمالي الخصم</span>
                        <span>{formatMoney(totals.discount_total)} {currencyLabel}</span>
                    </div>
                    <div className="flex justify-between py-2 border-b border-slate-100">
                        <span className="text-slate-600">الصافي</span>
                        <span className="font-bold">{formatMoney(totals.net_total)} {currencyLabel}</span>
                    </div>
                    <div className="flex justify-between py-2 border-b border-slate-100 text-green-600">
                        <span>المدفوع</span>
                        <span className="font-bold">{formatMoney(totals.paid_total)} {currencyLabel}</span>
                    </div>
                    <div className="flex justify-between py-2 text-xl font-bold text-slate-800">
                        <span>المتبقي</span>
                        <span>{formatMoney(totals.remaining_total)} {currencyLabel}</span>
                    </div>
                </div>
            </div>
            {/* Footer */}
            {(invoice.clinic_address || invoice.clinic_phone) && (
                <div className="fixed bottom-0 start-0 end-0 p-8 text-center text-slate-500 text-sm border-t border-slate-100">
                    {invoice.clinic_address && <p>عنوان العيادة: {invoice.clinic_address}</p>}
                    {invoice.clinic_phone && (
                        <p>تليفون: <span dir="ltr" className="font-mono">{invoice.clinic_phone}</span></p>
                    )}
                </div>
            )}
        </div>
    );
}
