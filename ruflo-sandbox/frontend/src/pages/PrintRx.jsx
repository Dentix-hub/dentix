import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getTenantSettings } from '../api';
import { Stethoscope, MapPin, Phone } from 'lucide-react';
export default function PrintRx() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [patient, setPatient] = useState(null);
    const [prescription, setPrescription] = useState(null);
    const [headerInfo, setHeaderInfo] = useState({
        doctor_name: 'اسم الطبيب',
        doctor_title: 'التخصص',
        clinic_address: 'العنوان',
        clinic_phone: '0000000000'
    });
    useEffect(() => {
        // Fetch Tenant Settings (Rx Header)
        getTenantSettings().then((res) => {
            if (res.data) {
                setHeaderInfo({
                    doctor_name: res.data.doctor_name || 'اسم الطبيب',
                    doctor_title: res.data.doctor_title || 'التخصص',
                    clinic_address: res.data.clinic_address || 'العنوان',
                    clinic_phone: res.data.clinic_phone || '0000000000',
                });
            }
        }).catch(err => console.error("Failed to fetch rx header info", err));
        // In a real app, you'd fetch the specific prescription by an ID
        // For now, let's look for state passed via router or fetch last one
        const data = sessionStorage.getItem('print_rx_data');
        if (data) {
            const parsed = JSON.parse(data);
            setPrescription(parsed.prescription);
            setPatient(parsed.patient);
            // Auto print and close tab/go back
            setTimeout(() => {
                window.print();
            }, 1000); // Increased delay slightly to ensure font loading
        }
    }, [id]);
    if (!patient || !prescription) return <div className="p-10 text-center text-slate-400">Loading Prescription Data...</div>;
    const medications = JSON.parse(prescription.medications);
    return (
        <div className="min-h-screen bg-white p-4 sm:p-10 font-['Cairo']" dir="rtl">
            <div className="max-w-2xl mx-auto border-2 border-slate-900 min-h-[90vh] flex flex-col p-8 relative overflow-hidden">
                {/* Header Decoration */}
                <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 -mr-16 -mt-16 rounded-full"></div>
                {/* Header */}
                <div className="flex justify-between items-start border-b-2 border-slate-900 pb-6 mb-8 relative z-10">
                    <div>
                        <h1 className="text-3xl font-extrabold text-slate-900 mb-1">{headerInfo.doctor_name}</h1>
                        <p className="text-lg font-bold text-primary">{headerInfo.doctor_title}</p>
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
                            <p className="text-slate-600 mr-4 flex items-center gap-2 italic">
                                <span>-</span>
                                <span>{med.dose}</span>
                            </p>
                        </div>
                    ))}
                </div>
                {/* Doctor's Notes */}
                {prescription.notes && (
                    <div className="mt-10 p-4 bg-yellow-50/50 rounded-lg border-r-4 border-yellow-400">
                        <h4 className="font-bold text-slate-700 mb-1 text-sm">ملاحظات إضافية:</h4>
                        <p className="text-slate-600">{prescription.notes}</p>
                    </div>
                )}
                {/* Footer Signature */}
                <div className="mt-auto pt-10 flex justify-end">
                    <div className="text-center w-48">
                        <div className="h-px bg-slate-300 mb-2"></div>
                        <p className="text-sm font-bold text-slate-400">توقيع الطبيب</p>
                    </div>
                </div>
                {/* Contact Info Footer */}
                <div className="mt-10 pt-6 border-t border-slate-200 flex flex-wrap justify-center gap-x-10 gap-y-2 text-sm text-slate-500">
                    <div className="flex items-center gap-2">
                        <Phone size={14} className="text-primary" />
                        <span dir="ltr">{headerInfo.clinic_phone}</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <MapPin size={14} className="text-primary" />
                        <span>{headerInfo.clinic_address}</span>
                    </div>
                </div>
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

