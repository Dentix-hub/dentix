export default function VisitDocumentation({ session, addenda = [], doctors = [], canAmend, onAmend, t }) {
    const author = (id) => doctors.find((doctor) => doctor.id === id)?.full_name || `#${id ?? '?'}`;
    return <section className="mt-2 space-y-2 text-xs" aria-label={t('care_session.visit_documentation', 'Visit documentation')}>
        {session.notes && <p className="whitespace-pre-wrap rounded-lg bg-surface p-2">{session.notes}</p>}
        {(session.procedures || []).filter((procedure) => procedure.procedure_notes || procedure.next_action || Object.keys(procedure.template_snapshot?.custom_field_values || {}).length).map((procedure) => <div key={procedure.id} className="rounded-lg border border-border p-2">
            <p className="font-bold">{procedure.template_snapshot?.title || procedure.template_code || `Procedure #${procedure.work_item_id}`}</p>
            <p className="whitespace-pre-wrap">{procedure.procedure_notes}</p>
            {procedure.next_action && <p>{t('care_session.next_action', 'Next action')}: {procedure.next_action}</p>}
            <dl>{(procedure.template_snapshot?.custom_fields || []).filter((field) => procedure.template_snapshot?.custom_field_values?.[field.field_id] != null).map((field) => <div key={field.field_id} className="flex gap-1">
                <dt>{field.label}:</dt><dd>{String(procedure.template_snapshot.custom_field_values[field.field_id])} {field.unit}</dd>
            </div>)}</dl>
        </div>)}
        <p className="text-text-secondary">{t('care_session.recorded_by', 'Recorded by')} {author(session.recorded_by_user_id || session.provider_user_id)} · {session.created_at ? new Date(session.created_at).toLocaleString() : '—'}</p>
        {addenda.map((entry) => <div key={entry.id} data-testid={`visit-addendum-${entry.id}`} className="rounded-lg border border-amber-200 bg-amber-50 p-2 text-amber-950 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-100">
            <p className="font-bold">{t('care_session.visit_correction', 'Visit correction')} · {author(entry.recorded_by_user_id)} · {new Date(entry.created_at).toLocaleString()}</p>
            <p className="whitespace-pre-wrap">{entry.notes}</p>
            <p>{t('care_session.correction_reason', 'Reason for correction')}: {entry.amendment_reason}</p>
        </div>)}
        {canAmend && session.status === 'completed' && <button type="button" data-testid={`add-visit-correction-${session.id}`} onClick={() => onAmend(session)} className="font-bold text-primary underline">{t('care_session.addendum_title', 'Add visit correction')}</button>}
    </section>;
}
