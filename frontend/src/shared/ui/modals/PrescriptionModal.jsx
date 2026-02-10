import { useState, useEffect } from 'react';
import { X, Star, Plus } from 'lucide-react';
import { getSavedMedications } from '@/api';
export default function PrescriptionModal({ isOpen, onClose, onPrint }) {
    const [drugs, setDrugs] = useState([{ name: '', dose: '' }]);
    const [notes, setNotes] = useState('');
    const [savedMeds, setSavedMeds] = useState([]);
    const [showSavedList, setShowSavedList] = useState(false);
    useEffect(() => {
        if (isOpen) {
            loadSavedMeds();
        }
    }, [isOpen]);
    const loadSavedMeds = async () => {
        try {
            const res = await getSavedMedications();
            setSavedMeds(res.data);
        } catch (err) {
            console.error("Failed to load saved medications", err);
        }
    };
    if (!isOpen) return null;
    const handleAddDrug = () => {
        setDrugs([...drugs, { name: '', dose: '' }]);
    };
    const handleSelectSavedMed = (med) => {
        // If the last line is empty, use it. Otherwise add new line.
        const lastDrug = drugs[drugs.length - 1];
        if (!lastDrug.name && !lastDrug.dose) {
            const newDrugs = [...drugs];
            newDrugs[drugs.length - 1] = { name: med.name, dose: med.default_dose };
            setDrugs(newDrugs);
        } else {
            setDrugs([...drugs, { name: med.name, dose: med.default_dose }]);
        }
        setShowSavedList(false);
    };
    const handlePrint = () => {
        onPrint({ drugs, notes });
    };
    return (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
            <div className="bg-white w-full max-w-2xl rounded-2xl p-6 shadow-2xl h-[80vh] flex flex-col">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-xl font-bold">كتابة روشتة</h3>
                    <button onClick={onClose}><X /></button>
                </div>
                <div className="flex-1 overflow-y-auto space-y-4 relative">
                    {/* Saved Meds Quick Access */}
                    {savedMeds.length > 0 && (
                        <div className="mb-4">
                            <button
                                onClick={() => setShowSavedList(!showSavedList)}
                                className="flex items-center gap-2 text-sm text-yellow-600 font-bold bg-yellow-50 px-3 py-2 rounded-lg hover:bg-yellow-100 transition-colors"
                            >
                                <Star size={16} className="fill-yellow-500" />
                                {showSavedList ? 'إخفاء الأدوية المحفوظة' : 'اختر من الأدوية المحفوظة'}
                            </button>
                            {showSavedList && (
                                <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-2 p-3 bg-slate-50 border border-slate-200 rounded-xl max-h-40 overflow-y-auto">
                                    {savedMeds.map(med => (
                                        <button
                                            key={med.id}
                                            onClick={() => handleSelectSavedMed(med)}
                                            className="text-right p-2 hover:bg-white rounded-lg border border-transparent hover:border-slate-200 transition-all flex flex-col items-start gap-1"
                                        >
                                            <span className="font-bold text-slate-800 text-sm" dir="ltr">{med.name}</span>
                                            <span className="text-xs text-slate-500">{med.default_dose}</span>
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                    {drugs.map((d, i) => (
                        <div key={i} className="flex gap-2">
                            <input
                                value={d.name}
                                onChange={e => { const n = [...drugs]; n[i].name = e.target.value; setDrugs(n); }}
                                placeholder="الدواء"
                                className="flex-1 p-3 bg-slate-50 rounded-xl outline-none"
                                dir="ltr"
                            />
                            <input
                                value={d.dose}
                                onChange={e => { const n = [...drugs]; n[i].dose = e.target.value; setDrugs(n); }}
                                placeholder="الجرعة"
                                className="w-1/3 p-3 bg-slate-50 rounded-xl outline-none"
                            />
                            {drugs.length > 1 && (
                                <button onClick={() => setDrugs(drugs.filter((_, idx) => idx !== i))} className="text-red-500 font-bold px-2">X</button>
                            )}
                        </div>
                    ))}
                    <button onClick={handleAddDrug} className="text-primary text-sm font-bold hover:underline flex items-center gap-1">
                        <Plus size={16} />
                        دواء آخر
                    </button>
                    <textarea
                        value={notes}
                        onChange={e => setNotes(e.target.value)}
                        placeholder="تعليمات إضافية"
                        className="w-full p-3 bg-slate-50 rounded-xl mt-4 h-32 outline-none"
                    />
                </div>
                <div className="flex justify-end gap-3 mt-4">
                    <button onClick={onClose} className="px-4 py-2 hover:bg-slate-100 rounded-lg">إلغاء</button>
                    <button onClick={handlePrint} className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700">طباعة وحفظ</button>
                </div>
            </div>
        </div>
    );
}
