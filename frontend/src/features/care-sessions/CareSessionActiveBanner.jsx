import ProtectedImage from '@/features/clinical-attachments/components/ProtectedImage';
import PropTypes from 'prop-types';
import { Activity, Clock, Flag, CheckCircle2, Calendar, Camera } from 'lucide-react';

export default function CareSessionActiveBanner({
    session,
    onOpenWorkflow,
    onOpenFinishSheet,
    attachmentLinks = [],
    autosaveIndicator = null,
    t = (key, fallback) => fallback || key,
}) {
    if (!session || session.status !== 'in_progress') return null;
    const sessionImages = (attachmentLinks || []).filter(
        (link) =>
            String(link.care_session_id) === String(session.id) &&
            (link.file_type?.includes('image') ||
                link.content_type?.includes('image') ||
                /\.(png|jpg|jpeg|webp|gif|svg)$/i.test(link.filename || link.file_name || '') ||
                (!link.file_type && !link.content_type)),
    );
    const steps = session.steps || [];
    const completedCount = steps.filter((step) => ['completed', 'partial'].includes(step.status)).length;
    const start = session.started_at ? new Date(session.started_at) : null;

    return (
        <aside
            aria-label={t('care_session.active_banner_title', 'Active Care Session')}
            data-testid="care-session-active-banner"
            className="min-w-0 space-y-3 rounded-card border border-primary/25 bg-primary/5 p-3 sm:p-4"
        >
            <div className="flex min-w-0 items-start gap-3">
                <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-control bg-primary text-white">
                    <Activity className="h-5 w-5" aria-hidden="true" />
                </span>
                <div className="min-w-0 flex-1 space-y-2">
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                        <h3 className="break-words text-sm font-bold text-text-primary">
                            {t('care_session.active_banner_title', 'Active Care Session')}{' '}
                            <bdi dir="ltr">#{session.id}</bdi>
                        </h3>
                        {autosaveIndicator}
                    </div>
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-xs text-text-secondary">
                        {start && !Number.isNaN(start.getTime()) && (
                            <span className="inline-flex items-center gap-1">
                                <Clock className="h-3.5 w-3.5" aria-hidden="true" />
                                <bdi dir="ltr">
                                    {start.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </bdi>
                            </span>
                        )}
                        {session.appointment_id && (
                            <span
                                data-testid="linked-appointment-badge"
                                className="inline-flex items-center gap-1"
                            >
                                <Calendar className="h-3.5 w-3.5" aria-hidden="true" />
                                {t('care_session.appointment_label', 'Appt')}{' '}
                                <bdi dir="ltr">#{session.appointment_id}</bdi>
                            </span>
                        )}
                        <span>
                            {steps.length
                                ? t(
                                      'care_session.steps_addressed',
                                      `${completedCount} of ${steps.length} steps addressed`,
                                      { completed: completedCount, total: steps.length },
                                  )
                                : t('care_session.session_in_progress', 'Chairside treatment in progress')}
                        </span>
                        {session.observations?.length > 0 && (
                            <span className="inline-flex items-center gap-1">
                                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" aria-hidden="true" />
                                <bdi dir="ltr">{session.observations.length}</bdi>{' '}
                                {t('care_session.obs_added', 'measurements')}
                            </span>
                        )}
                        {sessionImages.length > 0 && (
                            <button type="button" onClick={onOpenWorkflow} data-testid="session-images-badge" className="inline-flex min-h-10 items-center gap-1.5 rounded-control px-2 text-primary hover:bg-primary/10">
                                <Camera className="h-3.5 w-3.5" aria-hidden="true" />
                                <bdi dir="ltr">{sessionImages.length}</bdi> {t('care_session.images', 'images')}
                            </button>
                        )}
                    </div>
                </div>
            </div>
            {sessionImages.length > 0 && (
                <div data-testid="banner-session-images-strip" className="flex flex-wrap gap-2">
                    {sessionImages.slice(0, 3).map((image) => (
                        <ProtectedImage
                            key={image.id}
                            filePath={image.file_path}
                            thumbnail
                            alt={image.filename || t('care_session.images', 'Images')}
                            data-testid={`banner-session-image-${image.id}`}
                            onClick={onOpenWorkflow}
                            className="h-11 w-11 cursor-pointer rounded-control border border-border object-cover"
                            title={image.filename}
                        />
                    ))}
                </div>
            )}
            <div className="grid grid-cols-1 gap-2 min-[360px]:grid-cols-2 sm:flex sm:flex-wrap">
                <button
                    type="button"
                    onClick={onOpenWorkflow}
                    data-testid="btn-open-active-workflow"
                    className="inline-flex min-h-11 min-w-0 items-center justify-center gap-2 rounded-control bg-primary px-3 py-2 text-sm font-bold text-white hover:bg-primary-600"
                >
                    <Activity className="h-4 w-4 shrink-0" aria-hidden="true" />
                    {t('care_session.open_visit', 'Open visit')}
                </button>
                <button
                    type="button"
                    onClick={onOpenFinishSheet}
                    data-testid="btn-banner-finish-session"
                    className="inline-flex min-h-11 min-w-0 items-center justify-center gap-2 rounded-control border border-border bg-surface px-3 py-2 text-sm font-semibold text-text-primary hover:bg-surface-hover"
                >
                    <Flag className="h-4 w-4 shrink-0 text-emerald-600" aria-hidden="true" />
                    {t('care_session.finish_session_btn', 'Finish Session')}
                </button>
            </div>
        </aside>
    );
}

CareSessionActiveBanner.propTypes = {
    session: PropTypes.object,
    onOpenWorkflow: PropTypes.func.isRequired,
    onOpenFinishSheet: PropTypes.func.isRequired,
    attachmentLinks: PropTypes.array,
    autosaveIndicator: PropTypes.node,
    t: PropTypes.func,
};
