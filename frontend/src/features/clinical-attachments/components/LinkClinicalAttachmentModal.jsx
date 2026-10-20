import { useState, useId } from 'react';
import PropTypes from 'prop-types';
import { Tag, Link2, Unlink, AlertCircle, Loader2 } from 'lucide-react';
import Modal from '@/shared/ui/Modal';
import { ATTACHMENT_PURPOSE_OPTIONS, buildAttachmentUrl } from '../attachmentUtils';

// Standard FDI permanent (11-48) and primary (51-85) tooth keys
const ALL_FDI_TEETH = [
    // Permanent Upper Right & Left
    '18', '17', '16', '15', '14', '13', '12', '11', '21', '22', '23', '24', '25', '26', '27', '28',
    // Permanent Lower Left & Right
    '48', '47', '46', '45', '44', '43', '42', '41', '31', '32', '33', '34', '35', '36', '37', '38',
    // Primary Upper Right & Left
    '55', '54', '53', '52', '51', '61', '62', '63', '64', '65',
    // Primary Lower Left & Right
    '85', '84', '83', '82', '81', '71', '72', '73', '74', '75',
];

export default function LinkClinicalAttachmentModal({
    isOpen,
    onClose,
    attachment,
    patientId: _patientId,
    activeCareSession = null,
    workItems = [],
    initialToothKey = null,
    initialSessionId = null,
    initialPurposeCode = 'PRE_OP_XRAY',
    existingLinks = [],
    onLinkCreated,
    onLinkDeleted,
    isArabic = false,
}) {
    const toothSelectId = useId();
    const sessionSelectId = useId();
    const workItemSelectId = useId();
    const purposeSelectId = useId();
    const notesInputId = useId();

    const [toothKey, setToothKey] = useState(initialToothKey || '');
    const [careSessionId, setCareSessionId] = useState(
        initialSessionId ? String(initialSessionId) : (activeCareSession?.id ? String(activeCareSession.id) : '')
    );
    const [workItemId, setWorkItemId] = useState('');
    const [purposeCode, setPurposeCode] = useState(initialPurposeCode || 'PRE_OP_XRAY');
    const [notes, setNotes] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [unlinkingId, setUnlinkingId] = useState(null);
    const [errorMessage, setErrorMessage] = useState(null);

    if (!attachment) return null;

    const attachmentLinks = existingLinks.filter(
        (link) => Number(link.attachment_id) === Number(attachment.id)
    );

    const handleSubmit = async (e) => {
        e.preventDefault();
        setErrorMessage(null);

        const payload = {
            attachment_id: Number(attachment.id),
            tooth_key: toothKey ? String(toothKey) : null,
            care_session_id: careSessionId ? Number(careSessionId) : null,
            work_item_id: workItemId ? Number(workItemId) : null,
            purpose_code: purposeCode || 'OTHER',
            notes: notes.trim() || null,
        };

        if (!payload.tooth_key && !payload.care_session_id && !payload.work_item_id) {
            setErrorMessage(
                isArabic
                    ? 'يجب تحديد سياق سريري واحد على الأقل (رقم السن، جلسة العلاج، أو الإجراء)'
                    : 'Please select at least one clinical context (Tooth, Care Session, or Work Item).'
            );
            return;
        }

        try {
            setIsSubmitting(true);
            await onLinkCreated?.(payload);
            setNotes('');
            onClose();
        } catch (err) {
            const detail =
                err?.response?.data?.detail ||
                err?.message ||
                (isArabic ? 'حدث خطأ أثناء ربط الملف' : 'Failed to create context link');
            setErrorMessage(detail);
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleUnlink = async (linkId) => {
        try {
            setUnlinkingId(linkId);
            await onLinkDeleted?.(linkId);
        } catch (err) {
            setErrorMessage(err?.response?.data?.detail || err?.message);
        } finally {
            setUnlinkingId(null);
        }
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={isArabic ? 'ربط الملف بالسياق السريري' : 'Link Attachment to Clinical Context'}
            size="lg"
        >
            <div className="space-y-5 p-5" data-testid="link-clinical-attachment-modal">
                {/* File preview header */}
                <div className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-900">
                    {attachment.file_type?.includes('image') ? (
                        <img
                            src={buildAttachmentUrl(attachment.file_path)}
                            alt={attachment.filename}
                            className="h-14 w-14 rounded-xl object-cover border border-slate-200 dark:border-slate-800"
                        />
                    ) : (
                        <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-blue-100 text-blue-600 dark:bg-blue-950/60 dark:text-blue-400">
                            <Tag className="h-6 w-6" />
                        </div>
                    )}
                    <div className="min-w-0 flex-1">
                        <h4 className="truncate text-sm font-bold text-slate-900 dark:text-slate-100">
                            {attachment.filename}
                        </h4>
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                            {attachment.file_type} • ID #{attachment.id}
                        </p>
                    </div>
                </div>

                {errorMessage && (
                    <div
                        role="alert"
                        data-testid="link-error-alert"
                        className="flex items-start gap-2.5 rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-800 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-300"
                    >
                        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                        <span>{errorMessage}</span>
                    </div>
                )}

                {/* Form to create context link */}
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                        {/* Tooth selection */}
                        <div>
                            <label
                                htmlFor={toothSelectId}
                                className="block text-xs font-bold text-slate-700 dark:text-slate-300"
                            >
                                {isArabic ? 'رقم السن (FDI)' : 'Tooth (FDI)'}
                            </label>
                            <select
                                id={toothSelectId}
                                value={toothKey}
                                onChange={(e) => setToothKey(e.target.value)}
                                data-testid="select-tooth-key"
                                className="mt-1 block min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                            >
                                <option value="">{isArabic ? '-- بدون سن محدد --' : '-- No specific tooth --'}</option>
                                {ALL_FDI_TEETH.map((t) => (
                                    <option key={t} value={t}>
                                        {isArabic ? `سن ${t}` : `Tooth ${t}`}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {/* Care Session selection */}
                        <div>
                            <label
                                htmlFor={sessionSelectId}
                                className="block text-xs font-bold text-slate-700 dark:text-slate-300"
                            >
                                {isArabic ? 'جلسة العلاج' : 'Care Session'}
                            </label>
                            <select
                                id={sessionSelectId}
                                value={careSessionId}
                                onChange={(e) => setCareSessionId(e.target.value)}
                                data-testid="select-care-session"
                                className="mt-1 block min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                            >
                                <option value="">{isArabic ? '-- بدون جلسة محددة --' : '-- No care session --'}</option>
                                {activeCareSession && (
                                    <option value={activeCareSession.id}>
                                        {isArabic
                                            ? `الجلسة الحالية (#${activeCareSession.id})`
                                            : `Active Session (#${activeCareSession.id})`}
                                    </option>
                                )}
                            </select>
                        </div>

                        {/* Work Item selection (optional) */}
                        <div>
                            <label
                                htmlFor={workItemSelectId}
                                className="block text-xs font-bold text-slate-700 dark:text-slate-300"
                            >
                                {isArabic ? 'الإجراء السريري' : 'Work Item'}
                            </label>
                            <select
                                id={workItemSelectId}
                                value={workItemId}
                                onChange={(e) => setWorkItemId(e.target.value)}
                                data-testid="select-work-item"
                                className="mt-1 block min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                            >
                                <option value="">{isArabic ? '-- بدون إجراء محدد --' : '-- No work item --'}</option>
                                {workItems.map((wi) => (
                                    <option key={wi.id} value={wi.id}>
                                        #{wi.id} - {wi.code} ({wi.kind || 'procedure'})
                                    </option>
                                ))}
                            </select>
                        </div>

                        {/* Purpose Code (PD05 allowlist) */}
                        <div>
                            <label
                                htmlFor={purposeSelectId}
                                className="block text-xs font-bold text-slate-700 dark:text-slate-300"
                            >
                                {isArabic ? 'تصنيف الغرض (Purpose Code)' : 'Purpose Code (PD05)'}
                            </label>
                            <select
                                id={purposeSelectId}
                                value={purposeCode}
                                onChange={(e) => setPurposeCode(e.target.value)}
                                data-testid="select-purpose-code"
                                className="mt-1 block min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                            >
                                {ATTACHMENT_PURPOSE_OPTIONS.map((opt) => (
                                    <option key={opt.value} value={opt.value}>
                                        {isArabic ? opt.labelAr : opt.labelEn}
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>

                    {/* Notes */}
                    <div>
                        <label
                            htmlFor={notesInputId}
                            className="block text-xs font-bold text-slate-700 dark:text-slate-300"
                        >
                            {isArabic ? 'ملاحظات سريرية' : 'Clinical Notes'}
                        </label>
                        <input
                            id={notesInputId}
                            type="text"
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            data-testid="input-link-notes"
                            placeholder={isArabic ? 'مثال: صورة شعاعية أولية لقياس القنوات' : 'e.g. Initial diagnostic radiograph'}
                            className="mt-1 block min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                        />
                    </div>

                    <div className="flex items-center justify-end gap-3 pt-2">
                        <button
                            type="button"
                            onClick={onClose}
                            className="inline-flex min-h-11 items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-xs font-bold text-slate-700 shadow-sm hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                        >
                            {isArabic ? 'إلغاء' : 'Cancel'}
                        </button>
                        <button
                            type="submit"
                            disabled={isSubmitting}
                            data-testid="btn-submit-link-attachment"
                            className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-blue-600 px-5 py-2 text-xs font-bold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
                        >
                            {isSubmitting ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                <Link2 className="h-4 w-4" />
                            )}
                            <span>{isArabic ? 'ربط بالسياق السريري' : 'Create Context Link'}</span>
                        </button>
                    </div>
                </form>

                {/* Existing links list */}
                {attachmentLinks.length > 0 && (
                    <div className="border-t border-slate-200 pt-4 dark:border-slate-800" data-testid="existing-links-section">
                        <h4 className="text-xs font-bold text-slate-700 dark:text-slate-300">
                            {isArabic ? 'الروابط السريرية الحالية' : 'Current Clinical Links'} ({attachmentLinks.length})
                        </h4>
                        <ul className="mt-2 space-y-2">
                            {attachmentLinks.map((link) => (
                                <li
                                    key={link.id}
                                    data-testid={`existing-link-item-${link.id}`}
                                    className="flex items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white p-2.5 text-xs dark:border-slate-800 dark:bg-slate-900"
                                >
                                    <div className="flex flex-wrap items-center gap-2">
                                        <span className="font-bold text-slate-800 dark:text-slate-200">
                                            {link.purpose_code}
                                        </span>
                                        {link.tooth_key && (
                                            <span className="rounded-md bg-purple-100 px-2 py-0.5 font-bold text-purple-800 dark:bg-purple-950/50 dark:text-purple-300">
                                                Tooth {link.tooth_key}
                                            </span>
                                        )}
                                        {link.care_session_id && (
                                            <span className="rounded-md bg-emerald-100 px-2 py-0.5 font-bold text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300">
                                                Session #{link.care_session_id}
                                            </span>
                                        )}
                                        {link.work_item_id && (
                                            <span className="rounded-md bg-amber-100 px-2 py-0.5 font-bold text-amber-800 dark:bg-amber-950/50 dark:text-amber-300">
                                                Item #{link.work_item_id}
                                            </span>
                                        )}
                                        {link.notes && (
                                            <span className="text-slate-500 italic truncate max-w-xs">
                                                ({link.notes})
                                            </span>
                                        )}
                                    </div>

                                    <button
                                        type="button"
                                        onClick={() => handleUnlink(link.id)}
                                        disabled={unlinkingId === link.id}
                                        data-testid={`btn-unlink-${link.id}`}
                                        aria-label={`Unlink context ${link.id}`}
                                        className="inline-flex min-h-9 min-w-9 items-center justify-center rounded-lg border border-red-200 bg-red-50 p-1.5 text-red-600 transition-colors hover:bg-red-100 disabled:opacity-50 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-400"
                                    >
                                        {unlinkingId === link.id ? (
                                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                        ) : (
                                            <Unlink className="h-3.5 w-3.5" />
                                        )}
                                    </button>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>
        </Modal>
    );
}

LinkClinicalAttachmentModal.propTypes = {
    isOpen: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    attachment: PropTypes.object,
    patientId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    activeCareSession: PropTypes.object,
    workItems: PropTypes.array,
    initialToothKey: PropTypes.string,
    initialSessionId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    initialPurposeCode: PropTypes.string,
    existingLinks: PropTypes.array,
    onLinkCreated: PropTypes.func,
    onLinkDeleted: PropTypes.func,
    isArabic: PropTypes.bool,
};
