import { useState, useEffect } from 'react';
import logger from '@/utils/logger';
import { useParams, useNavigate } from 'react-router-dom';
import { getPrescriptionPrint } from '../api';
import { Stethoscope, MapPin, Phone } from 'lucide-react';

export default function PrintRx() {
    // `id` is the REAL prescription id — data comes from a tenant-scoped
    // server DTO, never from stale sessionStorage PHI.
    const { id } = useParams();
    const navigate = useNavigate();
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        let cancelled = false;
        getPrescriptionPrint(id)
            .then((res) => {
                if (cancelled) return;
                setData(res.data);
                setTimeout(() => window.print(), 1000);
            })
            .catch((err) => {
                if (!cancelled) {
                    logger.error('Failed to fetch prescription print data', err);
                    setError('تعذر تحميل بيانات الوصفة');
                }
            });
        return () => { cancelled = true; };
    }, [id]);

    if (error) return <div className="p-10 text-center text-red-600">{error}</div>;
    if (!data) return <div className="p-10 text-center text-slate-500">Loading Prescription Data...</div>;

    const { prescription, patient, clinic } = data;
    const medications = JSON.parse(prescription.medications || '[]');
    return (
        <div className="min-h-screen bg-white p-4 sm:p-10 font-['Cairo']" dir="rtl">
            <div className="max-w-2xl mx-auto border-2 border-slate-900 min-h-[90vh] flex flex-col p-8 relative overflow-hidden">
                {/* Header Decoration */}
                <div className="absolute top-0 end-0 w-32 h-32 bg-primary/5 -me-16 -mt-16 rounded-full"></div>
                {/* Header */}
                <div className="flex justify-between items-start border-b-2 border-slate-900 pb-6 mb-8 relative z-10">
                    <div>
                        <h1 className="text-3xl font-extrabold text-slate-900 mb-1">{clinic.doctor_name || 'اسم الطبيب'}</h1>
                        <p className="text-lg font-bold text-primary">{clinic.doctor_title || 'التخصص'}</p>
                    </div>
                    <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center text-primary">
                        <Stethoscope size={40} />
                    </div>
                </div>
                {/* Patient Info Bar */}
                <div className="bg-slate-50 p-4 rounded-xl flex justify-between items-center mb-10 border border-slate-200">
                    <div className="flex gap-4">
                        <span className="font-bold text-slate-500">اسم المريض:</span>
                        <span className="font-bold text-slate-900">{patient.name}</span>
                    </div>
                    <div className="flex gap-4">
                        <span className="font-bold text-slate-500">التاريخ:</span>
                        <span className="font-bold text-slate-900">{new Date(prescription.date).toLocaleDateString('ar-EG')}</span>
                    </div>
                </div>
                {/* RX Symbol Area */}
                <div className="mb-6">
                    <span className="text-6xl font-serif text-slate-900 opacity-20">℞</span>
                </div>
                {/* Medications List */}
                <div className="flex-1 space-y-8 px-6">
                    {medications.map((med, index) => (
                        <div key={index} className="border-b border-slate-100 pb-4 last:border-0">
                            <h3 className="text-xl font-bold text-slate-900 mb-2 text-left" dir="auto">{med.name}</h3>
                            <p className="text-slate-600 me-4 flex items-center gap-2 italic">
                                <span>-</span>
                                <span>{med.dose}</span>
                            </p>
                        </div>
                    ))}
                </div>
                {/* Doctor's Notes */}
                {prescription.notes && (
                    <div className="mt-10 p-4 bg-yellow-50/50 rounded-lg border-e-4 border-yellow-400">
                        <h4 className="font-bold text-slate-700 mb-1 text-sm">ملاحظات إضافية:</h4>
                        <p className="text-slate-600">{prescription.notes}</p>
                    </div>
                )}
                {/* Footer Signature */}
                <div className="mt-auto pt-10 flex justify-end">
                    <div className="text-center w-48">
                        <div className="h-px bg-slate-300 mb-2"></div>
                        <p className="text-sm font-bold text-slate-500">توقيع الطبيب</p>
                    </div>
                </div>
                {/* Contact Info Footer */}
                {(clinic.clinic_address || clinic.clinic_phone) && (
                    <div className="mt-10 pt-6 border-t border-slate-200 flex flex-wrap justify-center gap-x-10 gap-y-2 text-sm text-slate-500">
                        {clinic.clinic_phone && (
                            <div className="flex items-center gap-2">
                                <Phone size={14} className="text-primary" />
                                <span dir="ltr">{clinic.clinic_phone}</span>
                            </div>
                        )}
                        {clinic.clinic_address && (
                            <div className="flex items-center gap-2">
                                <MapPin size={14} className="text-primary" />
                                <span>{clinic.clinic_address}</span>
                            </div>
                        )}
                    </div>
                )}
            </div>
            {/* Print Instructions Hide on Print */}
            <div className="mt-8 text-center print:hidden flex flex-col items-center gap-4">
                <p className="text-slate-500">انتهت المعاينة، سيتم فتح نافذة الطباعة تلقائياً.</p>
                <div className="flex gap-4">
                    <button
                        onClick={() => window.print()}
                        className="bg-primary text-white px-8 py-3 rounded-xl font-bold hover:shadow-lg transition-all"
                    >
                        إعادة طباعة
                    </button>
                    <button
                        onClick={() => {
                            if (window.opener) {
                                window.close();
                            } else {
                                navigate(-1);
                            }
                        }}
                        className="bg-slate-100 text-slate-600 px-8 py-3 rounded-xl font-bold hover:bg-slate-200 transition-all"
                    >
                        {window.opener ? 'إغلاق النافذة' : 'العودة للمريض'}
                    </button>
                </div>
            </div>
        </div>
    );
}
