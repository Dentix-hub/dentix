import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getPatient, getPatientTreatments, getPatientPayments } from '../api';

export default function PrintInvoice() {
    const { id } = useParams();
    const [patient, setPatient] = useState(null);
    const [items, setItems] = useState([]);
    const [payments, setPayments] = useState([]);

    useEffect(() => {
        async function fetchData() {
            const [p, t, pay] = await Promise.all([
                getPatient(id),
                getPatientTreatments(id),
                getPatientPayments(id)
            ]);
            setPatient(p.data);
            setItems(t.data);
            setPayments(pay.data);
            // Auto print after small delay
            setTimeout(() => window.print(), 500);
        }
        fetchData();
    }, [id]);

    if (!patient) return <div>Loading...</div>;

    const total = items.reduce((acc, curr) => acc + curr.cost, 0);
    const paid = payments.reduce((acc, curr) => acc + curr.amount, 0);
    const remaining = total - paid;

    return (
        <div className="bg-white p-8 min-h-screen font-cairo" dir="rtl">
            {/* Header */}
            <div className="flex justify-between items-end border-b-2 border-slate-800 pb-4 mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900">عيادة د. إسلام عمارة</h1>
                    <p className="text-slate-600 mt-1">لطب وجراحة الأسنان</p>
                </div>
                <div className="text-left text-sm text-slate-500">
                    <p>Date: {new Date().toLocaleDateString()}</p>
                    <p>Invoice #: {id}-{Date.now().toString().slice(-4)}</p>
                </div>
            </div>

            {/* Patient Info */}
            <div className="mb-8 p-4 bg-slate-50 rounded-lg border border-slate-200">
                <h2 className="text-lg font-bold mb-2">بيانات المريض</h2>
                <div className="grid grid-cols-2 gap-4">
                    <p><span className="text-slate-500">الاسم:</span> <span className="font-bold">{patient.name}</span></p>
                    <p><span className="text-slate-500">رقم الهاتف:</span> <span dir="ltr" className="font-mono">{patient.phone}</span></p>
                </div>
            </div>

            {/* Treatments Table */}
            <div className="mb-8">
                <table className="w-full text-right border-collapse">
                    <thead>
                        <tr className="border-b border-slate-300">
                            <th className="py-2 text-slate-600">الإجراء العلاجي</th>
                            <th className="py-2 text-slate-600 w-32">التاريخ</th>
                            <th className="py-2 text-slate-600 w-32">التكلفة</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items.map((item, index) => (
                            <tr key={index} className="border-b border-slate-100">
                                <td className="py-3 font-bold text-slate-800">{item.diagnosis} - {item.procedure} <span className="text-xs text-slate-400">({item.tooth_number || 'عام'})</span></td>
                                <td className="py-3 text-slate-600">{new Date(item.date).toLocaleDateString()}</td>
                                <td className="py-3 font-mono">{item.cost}</td>
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
                        <span className="font-bold text-lg">{total} ج.م</span>
                    </div>
                    <div className="flex justify-between py-2 border-b border-slate-100 text-green-600">
                        <span>المدفوع</span>
                        <span className="font-bold">{paid} ج.م</span>
                    </div>
                    <div className="flex justify-between py-2 text-xl font-bold text-slate-800">
                        <span>المتبقي</span>
                        <span>{remaining} ج.م</span>
                    </div>
                </div>
            </div>

            {/* Footer */}
            <div className="fixed bottom-0 left-0 right-0 p-8 text-center text-slate-400 text-sm border-t border-slate-100">
                <p>عنوان العيادة: شارع التحرير - أمام محطة المترو</p>
                <p>تليفون: 01000000000</p>
            </div>
        </div>
    );
}
