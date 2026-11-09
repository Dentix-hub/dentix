import { useState } from 'react';
import { Button, Modal } from '@/shared/ui';
import { addCareSessionAddendum } from '@/api/patients';

export default function CareSessionAddendumModal({ patientId, session, onClose, onSuccess, t }) {
    const [notes, setNotes] = useState('');
    const [reason, setReason] = useState('');
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');
    const submit = async (event) => {
        event.preventDefault();
        if (!notes.trim() || !reason.trim()) return;
        setSaving(true);
        try {
            await addCareSessionAddendum(patientId, session.id, { notes: notes.trim(), reason: reason.trim() });
            onSuccess();
        } catch (err) {
            const detail = err?.response?.data?.detail;
            setError(typeof detail === 'string' ? detail : t('care_session.addendum_failed', 'Unable to save the correction. Please try again.'));
        } finally {
            setSaving(false);
        }
    };
    return <Modal isOpen onClose={onClose} title={t('care_session.addendum_title', 'Add visit correction')} size="md">
        <form onSubmit={submit} className="space-y-4">
            <p className="text-sm text-text-secondary">{t('care_session.addendum_explanation', 'The original visit stays in the record. Your correction is saved with your name, recording time, and reason.')}</p>
            <blockquote className="whitespace-pre-wrap rounded-xl border border-border p-3 text-sm">{session.notes}</blockquote>
            <label className="block text-sm">{t('care_session.correction_text', 'Correction / addendum')}
                <textarea aria-label={t('care_session.correction_text', 'Correction / addendum')} required maxLength={20000} rows={4} value={notes} onChange={(event) => setNotes(event.target.value)} className="mt-1 w-full rounded-xl border border-border bg-surface p-2" />
            </label>
            <label className="block text-sm">{t('care_session.correction_reason', 'Reason for correction')}
                <input aria-label={t('care_session.correction_reason', 'Reason for correction')} required maxLength={500} value={reason} onChange={(event) => setReason(event.target.value)} className="mt-1 w-full rounded-xl border border-border bg-surface p-2" />
            </label>
            {error && <p role="alert" className="text-sm text-danger">{error}</p>}
            <Button type="submit" disabled={saving || !notes.trim() || !reason.trim()}>{saving ? t('common.saving', 'Saving...') : t('care_session.save_correction', 'Save correction')}</Button>
        </form>
    </Modal>;
}
