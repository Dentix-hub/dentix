import { useState } from 'react';
import { Download } from 'lucide-react';
import { useTranslation } from 'react-i18next';

function saveBlobResponse(response, fallbackName) {
    const blob = response?.data;
    if (!(blob instanceof Blob)) throw new Error('Export response is not a file');
    const disposition = response.headers?.['content-disposition'] || '';
    const match = disposition.match(/filename="?([^";]+)"?/i);
    const filename = match?.[1] || fallbackName;
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
}

export default function ExportCsvButton({
    onExport,
    disabled = false,
    filename = 'finance-export.csv',
    label,
    className = '',
}) {
    const { t } = useTranslation();
    const [isExporting, setIsExporting] = useState(false);
    const [error, setError] = useState('');

    const handleExport = async () => {
        setError('');
        setIsExporting(true);
        try {
            const response = await onExport();
            saveBlobResponse(response, filename);
        } catch {
            setError(t('finance.reports.export_failed', 'تعذر تصدير الملف. حاول مرة أخرى.'));
        } finally {
            setIsExporting(false);
        }
    };

    return (
        <div className={`flex flex-col items-stretch gap-1 ${className}`}>
            <button
                type="button"
                onClick={handleExport}
                disabled={disabled || isExporting}
                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-xl border border-border bg-card px-3 py-2 text-xs font-bold text-text-primary transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
            >
                <Download className="h-4 w-4" aria-hidden="true" />
                <span>
                    {isExporting
                        ? t('common.loading', 'جاري التحميل...')
                        : label || t('finance.reports.export_csv', 'تصدير CSV')}
                </span>
            </button>
            {error && (
                <span role="alert" className="text-[11px] font-semibold text-destructive">
                    {error}
                </span>
            )}
        </div>
    );
}
