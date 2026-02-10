import { useState } from 'react';
import { X } from 'lucide-react';
export default function PaymentModal({ isOpen, onClose, onAdd }) {
    const [payment, setPayment] = useState({ amount: '', notes: '', date: new Date().toISOString().split('T')[0] });
    if (!isOpen) return null;
    const handleSave = () => {
        // Ensure date is valid ISO datetime for backend
        const submissionData = {
            ...payment,
            date: payment.date ? `${payment.date}T00:00:00` : new Date().toISOString()
        };
        onAdd(submissionData);
        setPayment({ amount: '', notes: '', date: new Date().toISOString().split('T')[0] }); // Reset
    };
    return (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
            <div className="bg-white w-full max-w-md rounded-2xl p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-xl font-bold">إضافة دفعة مالية</h3>
                    <button onClick={onClose}><X /></button>
                </div>
                <div className="space-y-4">
                    <input
                        value={payment.amount}
                        onChange={e => setPayment({ ...payment, amount: e.target.value })}
                        placeholder="المبلغ المدفوع"
                        type="number"
                        className="w-full p-3 bg-slate-50 rounded-xl outline-none font-bold text-lg text-emerald-600"
                    />
                    <input
                        value={payment.date}
                        onChange={e => setPayment({ ...payment, date: e.target.value })}
                        type="date"
                        className="w-full p-3 bg-slate-50 rounded-xl outline-none text-slate-600"
                    />
                    <textarea
                        value={payment.notes}
                        onChange={e => setPayment({ ...payment, notes: e.target.value })}
                        placeholder="ملاحظات"
                        className="w-full p-3 bg-slate-50 rounded-xl outline-none"
                    />
                    <div className="flex justify-end gap-3">
                        <button onClick={onClose} className="px-4 py-2 hover:bg-slate-100 rounded-lg">إلغاء</button>
                        <button onClick={handleSave} className="px-6 py-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600">إضافة</button>
                    </div>
                </div>
            </div>
        </div>
    );
}
