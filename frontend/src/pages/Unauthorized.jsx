import { Link } from 'react-router-dom';
import { ShieldAlert } from 'lucide-react';

export default function Unauthorized() {
    return (
        <div className="min-h-screen flex flex-col items-center justify-center gap-6 p-8 text-center" dir="rtl">
            <div className="p-5 bg-red-50 text-red-500 rounded-3xl">
                <ShieldAlert size={56} />
            </div>
            <h1 className="text-3xl font-black text-slate-800 dark:text-white">صلاحيات غير كافية</h1>
            <p className="text-slate-500 max-w-md">
                لا تملك صلاحية الوصول إلى هذه الصفحة. تواصل مع مسؤول العيادة إذا كنت تعتقد أن هذا خطأ.
            </p>
            <Link
                to="/"
                className="px-8 py-3 bg-slate-800 hover:bg-slate-900 text-white rounded-xl font-bold shadow-lg transition-colors"
            >
                العودة للرئيسية
            </Link>
        </div>
    );
}
