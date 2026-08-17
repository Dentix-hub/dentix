import { useState } from 'react';
import { Download, FileSpreadsheet, Printer } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { getAllProceduresFinancials } from '@/api/financials';
import { toast } from '@/shared/ui';

export default function AnalyticsExportButton() {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';
    const [exporting, setExporting] = useState(false);

    const exportToCSV = async () => {
        setExporting(true);
        try {
            const res = await getAllProceduresFinancials();
            const data = Array.isArray(res.data) ? res.data : [];

            if (data.length === 0) {
                toast.error(isRtl ? 'لا توجد بيانات للتصدير' : 'No data available to export');
                return;
            }

            // Generate CSV content
            const headers = isRtl
                ? ['اسم الإجراء', 'السعر (ج.م)', 'التكلفة الفعليه (AI)', 'هامش الربح (%)', 'عدد المواد']
                : ['Procedure Name', 'Price (EGP)', 'Cost (AI)', 'Profit Margin (%)', 'Materials Count'];

            const rows = data.map(item => [
                `"${item.name || ''}"`,
                item.price || 0,
                item.cost || 0,
                `${item.margin_percent || 0}%`,
                item.materials_count || 0
            ]);

            const csvContent = '\uFEFF' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `DENTIX_Procedures_Analytics_${new Date().toISOString().slice(0, 10)}.csv`);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            toast.success(isRtl ? 'تم تصدير ملف CSV بنجاح' : 'CSV exported successfully');
        } catch (err) {
            toast.error(isRtl ? 'فشل التصدير' : 'Export failed');
        } finally {
            setExporting(false);
        }
    };

    const handlePrint = () => {
        window.print();
    };

    return (
        <div className="flex items-center gap-2">
            <button
                onClick={exportToCSV}
                disabled={exporting}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold shadow-sm transition-all active:scale-95 disabled:opacity-50"
            >
                <FileSpreadsheet size={14} />
                <span>{exporting ? (isRtl ? 'جاري التصدير...' : 'Exporting...') : (isRtl ? 'تصدير CSV' : 'Export CSV')}</span>
            </button>
            <button
                onClick={handlePrint}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-surface hover:bg-surface-hover text-text-primary rounded-xl text-xs font-bold border border-border/50 transition-all active:scale-95"
                title={isRtl ? 'طباعة التقرير' : 'Print Report'}
            >
                <Printer size={14} />
                <span>{isRtl ? 'طباعة' : 'Print'}</span>
            </button>
        </div>
    );
}
