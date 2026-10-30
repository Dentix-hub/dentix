import ProtectedImage from '@/features/clinical-attachments/components/ProtectedImage';
import { getDriveImageStatus } from '@/api';
import { useState } from 'react';
import PropTypes from 'prop-types';
import { Upload, RefreshCw, Edit2, Trash2, FileText, File as FileIcon, Link2, Eye } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
    usePatientClinicalAttachmentLinks,
    useCreateClinicalAttachmentLink,
    useDeleteClinicalAttachmentLink,
} from '@/hooks/usePatientDetails';
import {
    buildAttachmentUrl,
    getPurposeLabel,
    DiagnosticImageLightbox,
    LinkClinicalAttachmentModal,
} from '@/features/clinical-attachments';

const PatientFiles = ({
    attachments = [],
    handleFileUpload,
    handleDeleteAttachment,
    loading,
    reloadAttachments,
    isPollingStalled = false,
    patientId = null,
    activeCareSession = null,
    workItems = [],
    attachmentLinks: propAttachmentLinks = null,
    onCreateAttachmentLink = null,
    onDeleteAttachmentLink = null,
}) => {
    const { t, i18n } = useTranslation();
    const isArabic = i18n?.language?.startsWith('ar');

    // Query links from hook if not supplied via props
    const { data: fetchedLinks = [], refetch: refetchLinks } = usePatientClinicalAttachmentLinks(
        patientId,
        {},
        { enabled: Boolean(patientId) && propAttachmentLinks === null }
    );
    const activeLinks = propAttachmentLinks !== null ? propAttachmentLinks : fetchedLinks;

    const createLinkMutation = useCreateClinicalAttachmentLink();
    const deleteLinkMutation = useDeleteClinicalAttachmentLink();

    const [selectedAttachmentForLink, setSelectedAttachmentForLink] = useState(null);
    const [selectedImageForLightbox, setSelectedImageForLightbox] = useState(null);
    const [imageMessages, setImageMessages] = useState({});
    const [retryGeneration, setRetryGeneration] = useState(0);
    const showImageStatus = async (file) => {
        try {
            const response = await getDriveImageStatus(file.file_path);
            setImageMessages((current) => ({ ...current, [file.id]: response.data.message || t('backup.image_unavailable') }));
        } catch {
            setImageMessages((current) => ({ ...current, [file.id]: t('backup.image_unavailable') }));
        }
    };

    const handleOpenLinkModal = (file, e) => {
        e?.stopPropagation();
        setSelectedAttachmentForLink(file);
    };

    const handleCreateLink = async (payload) => {
        if (onCreateAttachmentLink) {
            await onCreateAttachmentLink(payload);
        } else if (patientId) {
            await createLinkMutation.mutateAsync({ patientId, data: payload });
            refetchLinks();
        }
    };

    const handleDeleteLink = async (linkId) => {
        if (onDeleteAttachmentLink) {
            await onDeleteAttachmentLink(linkId);
        } else if (patientId) {
            await deleteLinkMutation.mutateAsync({ patientId, linkId });
            refetchLinks();
        }
    };

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
            <div className="flex justify-between items-center bg-white p-4 rounded-xl border border-slate-100 shadow-sm dark:border-slate-800 dark:bg-slate-900">
                <h3 className="font-bold text-slate-700 dark:text-slate-200 flex items-center gap-2">
                    <FileIcon size={20} className="text-slate-500" />
                    {t('patientDetails.files.title')}
                </h3>
                <div className="flex gap-2">
                    <button
                        type="button"
                        onClick={() => {
                            setRetryGeneration((prev) => prev + 1);
                            if (reloadAttachments) reloadAttachments();
                        }}
                        className="p-2 text-slate-500 hover:text-primary hover:bg-slate-50 rounded-lg transition-colors dark:hover:bg-slate-800"
                        title={t('patientDetails.files.refresh_tooltip')}
                    >
                        <RefreshCw size={20} className={loading ? 'animate-spin' : ''} />
                    </button>
                    <label className="flex items-center gap-2 px-4 py-2 bg-primary text-white font-bold rounded-lg hover:bg-sky-600 cursor-pointer transition-colors shadow-lg shadow-primary/20">
                        <Upload size={18} />
                        {t('patientDetails.files.upload')}
                        <input type="file" className="hidden" onChange={handleFileUpload} accept="image/*,.pdf" />
                    </label>
                </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
                {(Array.isArray(attachments) ? attachments : []).map((file) => {
                    const linksForFile = (activeLinks || []).filter(
                        (l) => Number(l.attachment_id) === Number(file.id)
                    );
                    const isImage = file.file_type?.includes('image');

                    return (
                        <div
                            key={file.id}
                            data-testid={`attachment-card-${file.id}`}
                            className="group relative aspect-square bg-slate-100 rounded-xl overflow-hidden border border-slate-200 shadow-sm dark:border-slate-800 dark:bg-slate-900"
                        >
                            {isImage ? (
                                <ProtectedImage
                                    filePath={file.file_path}
                                    thumbnail
                                    storageStatus={file.storage_status}
                                    retryGeneration={retryGeneration}
                                    alt={file.filename}
                                    className="w-full h-full object-cover transition-transform group-hover:scale-105 cursor-pointer"
                                    onClick={() => {
                                        const primaryLink = linksForFile[0];
                                        setSelectedImageForLightbox({
                                            ...file,
                                            purpose_code: primaryLink?.purpose_code,
                                            tooth_key: primaryLink?.tooth_key,
                                            care_session_id: primaryLink?.care_session_id,
                                            work_item_id: primaryLink?.work_item_id,
                                            notes: primaryLink?.notes,
                                        });
                                    }}
                                />
                            ) : (
                                <div className="w-full h-full flex flex-col items-center justify-center text-slate-500 p-4 text-center dark:text-slate-400">
                                    <FileText size={40} className="mb-2" />
                                    <span className="text-xs truncate w-full">{file.filename}</span>
                                </div>
                            )}

                            {file.storage_status && file.storage_status !== 'ready' && <div className="absolute inset-x-0 top-0 z-10 bg-amber-50 p-2 text-xs text-amber-900" role="status">
                                <span>
                                    {isPollingStalled && (file.storage_status === 'pending' || file.storage_status === 'deleting')
                                        ? t('backup.operation_delayed')
                                        : file.storage_status === 'pending'
                                        ? t('backup.image_pending')
                                        : file.storage_status === 'deleting'
                                        ? t('backup.image_deleting')
                                        : t('backup.image_unavailable')}
                                </span>
                                {isPollingStalled && (file.storage_status === 'pending' || file.storage_status === 'deleting') && reloadAttachments && (
                                    <button
                                        type="button"
                                        className="ms-2 underline font-medium text-amber-950 hover:text-black cursor-pointer"
                                        onClick={() => reloadAttachments()}
                                    >
                                        {t('backup.refresh_status')}
                                    </button>
                                )}
                                {file.storage_status === 'failed' && <button type="button" className="ms-2 underline" onClick={() => showImageStatus(file)}>{t('backup.image_details')}</button>}
                                {imageMessages[file.id] && <p>{imageMessages[file.id]}</p>}
                            </div>}
                            {/* Clinical Context Badges Overlay (G15-M03..M05) */}
                            {linksForFile.length > 0 && (
                                <div
                                    data-testid={`attachment-context-badges-${file.id}`}
                                    className="absolute top-2 start-2 end-2 flex flex-wrap gap-1 pointer-events-none"
                                >
                                    {linksForFile.map((lnk) => (
                                        <div key={lnk.id} className="flex flex-wrap gap-1">
                                            {lnk.tooth_key && (
                                                <span
                                                    data-testid={`badge-tooth-${lnk.tooth_key}`}
                                                    className="rounded-md bg-purple-600/90 text-white px-1.5 py-0.5 text-[10px] font-bold shadow-sm backdrop-blur-xs"
                                                >
                                                    T{lnk.tooth_key}
                                                </span>
                                            )}
                                            {lnk.care_session_id && (
                                                <span
                                                    data-testid={`badge-session-${lnk.care_session_id}`}
                                                    className="rounded-md bg-emerald-600/90 text-white px-1.5 py-0.5 text-[10px] font-bold shadow-sm backdrop-blur-xs"
                                                >
                                                    S#{lnk.care_session_id}
                                                </span>
                                            )}
                                            {lnk.purpose_code && (
                                                <span
                                                    data-testid={`badge-purpose-${lnk.purpose_code}`}
                                                    className="rounded-md bg-blue-600/90 text-white px-1.5 py-0.5 text-[10px] font-bold shadow-sm backdrop-blur-xs"
                                                >
                                                    {getPurposeLabel(lnk.purpose_code, isArabic)}
                                                </span>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Actions Overlay */}
                            <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                                {isImage && (
                                    <button
                                        type="button"
                                        onClick={() => {
                                            const primaryLink = linksForFile[0];
                                            setSelectedImageForLightbox({
                                                ...file,
                                                purpose_code: primaryLink?.purpose_code,
                                                tooth_key: primaryLink?.tooth_key,
                                                care_session_id: primaryLink?.care_session_id,
                                                work_item_id: primaryLink?.work_item_id,
                                                notes: primaryLink?.notes,
                                            });
                                        }}
                                        data-testid={`btn-preview-attachment-${file.id}`}
                                        aria-label={`Preview ${file.filename}`}
                                        className="p-2 bg-white rounded-full text-slate-700 hover:text-primary hover:scale-110 transition-all shadow-md"
                                    >
                                        <Eye size={16} />
                                    </button>
                                )}

                                {/* Link Clinical Context Action (G15-M02..M05) */}
                                <button
                                    type="button"
                                    onClick={(e) => handleOpenLinkModal(file, e)}
                                    data-testid={`btn-link-attachment-${file.id}`}
                                    aria-label={`Link clinical context for ${file.filename}`}
                                    className="p-2 bg-white rounded-full text-slate-700 hover:text-blue-600 hover:scale-110 transition-all shadow-md"
                                    title={isArabic ? 'ربط بالسياق السريري' : 'Link Clinical Context'}
                                >
                                    <Link2 size={16} />
                                </button>

                                <button
                                    type="button"
                                    onClick={() => window.open(buildAttachmentUrl(file.file_path), '_blank')}
                                    className="p-2 bg-white rounded-full text-slate-700 hover:text-primary hover:scale-110 transition-all shadow-md"
                                    aria-label={`Open ${file.filename}`}
                                >
                                    <Edit2 size={16} />
                                </button>
                                <button
                                    type="button"
                                    onClick={() => handleDeleteAttachment(file.id)}
                                    className="p-2 bg-white rounded-full text-slate-700 hover:text-red-500 hover:scale-110 transition-all shadow-md"
                                    aria-label={`Delete ${file.filename}`}
                                >
                                    <Trash2 size={16} />
                                </button>
                            </div>

                            <div className="absolute bottom-0 start-0 end-0 p-2 bg-gradient-to-t from-black/70 to-transparent text-white text-[11px] truncate flex justify-between items-center">
                                <span className="truncate">{file.filename}</span>
                                <span className="shrink-0 text-[10px] opacity-80 ms-1">
                                    {new Date(file.created_at).toLocaleDateString()}
                                </span>
                            </div>
                        </div>
                    );
                })}

                {attachments.length === 0 && (
                    <div className="col-span-full py-12 text-center text-slate-500 bg-slate-50 border border-dashed border-slate-200 rounded-xl dark:border-slate-800 dark:bg-slate-900/40">
                        <Upload size={48} className="mx-auto mb-3 opacity-20" />
                        <p>{t('patientDetails.files.empty')}</p>
                    </div>
                )}
            </div>

            {/* Context Linking Modal */}
            {selectedAttachmentForLink && (
                <LinkClinicalAttachmentModal
                    isOpen={Boolean(selectedAttachmentForLink)}
                    onClose={() => setSelectedAttachmentForLink(null)}
                    attachment={selectedAttachmentForLink}
                    patientId={patientId}
                    activeCareSession={activeCareSession}
                    workItems={workItems}
                    existingLinks={activeLinks}
                    onLinkCreated={handleCreateLink}
                    onLinkDeleted={handleDeleteLink}
                    isArabic={isArabic}
                />
            )}

            {/* Full Image Preview Lightbox */}
            {selectedImageForLightbox && (
                <DiagnosticImageLightbox
                    isOpen={Boolean(selectedImageForLightbox)}
                    onClose={() => setSelectedImageForLightbox(null)}
                    image={selectedImageForLightbox}
                    isArabic={isArabic}
                />
            )}
        </div>
    );
};

PatientFiles.propTypes = {
    attachments: PropTypes.array,
    handleFileUpload: PropTypes.func,
    handleDeleteAttachment: PropTypes.func,
    loading: PropTypes.bool,
    reloadAttachments: PropTypes.func,
    isPollingStalled: PropTypes.bool,
    patientId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    activeCareSession: PropTypes.object,
    workItems: PropTypes.array,
    attachmentLinks: PropTypes.array,
    onCreateAttachmentLink: PropTypes.func,
    onDeleteAttachmentLink: PropTypes.func,
};

export default PatientFiles;
