import { useState } from 'react';
import { Modal } from '@/shared/ui';
import ProtectedImage from '@/features/clinical-attachments/components/ProtectedImage';
import { DiagnosticImageLightbox, LinkClinicalAttachmentModal, getPurposeLabel } from '@/features/clinical-attachments';
import { usePatientAttachments, usePatientClinicalAttachmentLinks, useCreateClinicalAttachmentLink, useDeleteClinicalAttachmentLink } from '@/hooks/usePatientDetails';

export default function CareSessionImagesModal({ patientId, session, workItem, onClose, t }) {
    const files = usePatientAttachments(patientId);
    const links = usePatientClinicalAttachmentLinks(patientId, { care_session_id: session.id });
    const createLink = useCreateClinicalAttachmentLink();
    const deleteLink = useDeleteClinicalAttachmentLink();
    const [attachmentId, setAttachmentId] = useState('');
    const [preview, setPreview] = useState(null);
    const isImage = (item) => (item.content_type || item.file_type || '').startsWith('image/') || /\.(png|jpe?g|webp|gif)$/i.test(item.filename || item.file_name || item.file_path || '');
    const attachments = (files.data || []).filter(isImage);
    const visitImages = (links.data || []).filter((item) => isImage(item) && (!item.work_item_id || item.work_item_id === workItem.id));
    const selected = attachments.find((item) => item.id === Number(attachmentId));

    return <Modal isOpen onClose={onClose} title={t('care_session.images_tab', 'Images & X-Rays')} size="xl">
        <div className="space-y-4" data-testid="care-session-images">
            {(files.isError || links.isError) && <p role="alert">{t('care_session.images_load_error', 'Unable to load images. Close and try again.')}</p>}
            <label className="block text-sm">{t('care_session.link_image', 'Link Image to Session')}
                <select aria-label={t('care_session.link_image', 'Link Image to Session')} value={attachmentId} onChange={(event) => setAttachmentId(event.target.value)} className="mt-1 w-full rounded-xl border border-border bg-surface p-2">
                    <option value="">{t('common.select', 'Select')}</option>
                    {attachments.map((item) => <option key={item.id} value={item.id}>{item.filename || item.file_name}</option>)}
                </select>
            </label>
            {!files.isLoading && attachments.length === 0 && <p className="text-sm text-text-secondary">{t('care_session.upload_patient_files', 'Upload an image in the patient’s Files tab to link it here.')}</p>}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                {visitImages.map((item) => <button key={item.id} type="button" onClick={() => setPreview(item)} className="overflow-hidden rounded-xl border border-border p-2 text-xs">
                    <ProtectedImage filePath={item.file_path} thumbnail alt={item.filename || 'Visit image'} className="h-32 w-full object-cover" />
                    <span>{item.filename} · {getPurposeLabel(item.purpose_code)}</span>
                </button>)}
            </div>
            {!links.isLoading && !visitImages.length && <p className="text-sm text-text-secondary">{t('care_session.no_images', 'No diagnostic images linked to this care session yet.')}</p>}
        </div>
        {selected && <LinkClinicalAttachmentModal key={selected.id} isOpen attachment={selected} patientId={patientId} activeCareSession={session} initialSessionId={session.id} initialWorkItemId={workItem.id} initialToothKey={workItem.targets?.[0]?.tooth_key} workItems={[workItem]} existingLinks={links.data || []} onClose={() => setAttachmentId('')} onLinkCreated={(data) => createLink.mutateAsync({ patientId, data })} onLinkDeleted={(linkId) => deleteLink.mutateAsync({ patientId, linkId })} />}
        {preview && <DiagnosticImageLightbox isOpen image={preview} onClose={() => setPreview(null)} />}
    </Modal>;
}
