import ProtectedImage from './ProtectedImage';
import PropTypes from 'prop-types';
import { ExternalLink, Tag, Calendar, Activity, Info } from 'lucide-react';
import Modal from '@/shared/ui/Modal';
import { buildAttachmentUrl, getPurposeLabel } from '../attachmentUtils';

export default function DiagnosticImageLightbox({
    isOpen,
    onClose,
    image,
    isArabic = false,
}) {
    if (!image) return null;

    const fullUrl = buildAttachmentUrl(image.file_path);
    const purposeText = getPurposeLabel(image.purpose_code, isArabic);

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={image.filename || (isArabic ? 'معاينة الصورة' : 'Image Preview')}
            size="xl"
        >
            <div className="space-y-4 p-4" data-testid="diagnostic-image-lightbox">
                {/* Image display container */}
                <div className="flex max-h-[65vh] w-full items-center justify-center overflow-hidden rounded-2xl bg-black/90 p-2">
                    <ProtectedImage
                        filePath={image.file_path}
                        alt={image.filename || 'Diagnostic Radiograph'}
                        className="max-h-[60vh] max-w-full rounded-lg object-contain shadow-md"
                    />
                </div>

                {/* Metadata badges and context */}
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-900">
                    <div className="flex flex-wrap items-center gap-2">
                        {image.purpose_code && (
                            <span
                                data-testid="lightbox-purpose-badge"
                                className="inline-flex items-center gap-1 rounded-lg bg-blue-100 px-2.5 py-1 text-xs font-bold text-blue-800 dark:bg-blue-950/60 dark:text-blue-300"
                            >
                                <Tag className="h-3.5 w-3.5" aria-hidden="true" />
                                <span>{purposeText}</span>
                            </span>
                        )}

                        {image.tooth_key && (
                            <span
                                data-testid="lightbox-tooth-badge"
                                className="inline-flex items-center gap-1 rounded-lg bg-purple-100 px-2.5 py-1 text-xs font-bold text-purple-800 dark:bg-purple-950/60 dark:text-purple-300"
                            >
                                <span>{isArabic ? `السن ${image.tooth_key}` : `Tooth ${image.tooth_key}`}</span>
                            </span>
                        )}

                        {image.care_session_id && (
                            <span
                                data-testid="lightbox-session-badge"
                                className="inline-flex items-center gap-1 rounded-lg bg-emerald-100 px-2.5 py-1 text-xs font-bold text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"
                            >
                                <Activity className="h-3.5 w-3.5" aria-hidden="true" />
                                <span>{isArabic ? `جلسة #${image.care_session_id}` : `Session #${image.care_session_id}`}</span>
                            </span>
                        )}

                        {image.work_item_id && (
                            <span
                                data-testid="lightbox-workitem-badge"
                                className="inline-flex items-center gap-1 rounded-lg bg-amber-100 px-2.5 py-1 text-xs font-bold text-amber-800 dark:bg-amber-950/60 dark:text-amber-300"
                            >
                                <span>{isArabic ? `إجراء #${image.work_item_id}` : `Work Item #${image.work_item_id}`}</span>
                            </span>
                        )}
                    </div>

                    {image.created_at && (
                        <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
                            <Calendar className="h-3.5 w-3.5" />
                            <span>{new Date(image.created_at).toLocaleDateString()}</span>
                        </div>
                    )}
                </div>

                {image.notes && (
                    <div className="flex items-start gap-2 rounded-xl border border-slate-200 bg-white p-3 text-xs text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
                        <Info className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />
                        <p>{image.notes}</p>
                    </div>
                )}

                {/* Actions */}
                <div className="flex items-center justify-end gap-3 pt-2">
                    <button
                        type="button"
                        onClick={() => window.open(fullUrl, '_blank', 'noopener,noreferrer')}
                        data-testid="btn-open-image-external"
                        className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-xs font-bold text-slate-700 shadow-sm transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                    >
                        <ExternalLink className="h-4 w-4" aria-hidden="true" />
                        <span>{isArabic ? 'فتح في نافذة جديدة' : 'Open in New Tab'}</span>
                    </button>
                    <button
                        type="button"
                        onClick={onClose}
                        data-testid="btn-close-lightbox"
                        className="inline-flex min-h-11 items-center justify-center rounded-xl bg-slate-900 px-5 py-2 text-xs font-bold text-white shadow-sm transition-colors hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
                    >
                        {isArabic ? 'إغلاق' : 'Close'}
                    </button>
                </div>
            </div>
        </Modal>
    );
}

DiagnosticImageLightbox.propTypes = {
    isOpen: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    image: PropTypes.object,
    isArabic: PropTypes.bool,
};
