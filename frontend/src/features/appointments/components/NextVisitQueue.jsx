import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
    Clock,
    Calendar,
    User,
    Phone,
    CalendarPlus,
    X,
    Inbox,
    ChevronDown,
    ChevronUp
} from 'lucide-react';
import { Button, Badge, EmptyState } from '@/shared/ui';

export default function NextVisitQueue({
    requests = [],
    isLoading = false,
    onSchedule,
    onDismiss,
    className = '',
}) {
    const { i18n } = useTranslation();
    const isAr = i18n.language === 'ar';
    const [statusFilter, setStatusFilter] = useState('requested');
    const [isCollapsed, setIsCollapsed] = useState(false);

    const filteredRequests = requests.filter(r => {
        if (statusFilter === 'all') return true;
        return r.status === statusFilter;
    });

    const pendingCount = requests.filter(r => r.status === 'requested').length;

    const formatDateTime = (val) => {
        if (!val) return null;
        try {
            return new Date(val).toLocaleString(
                isAr ? 'ar-EG' : 'en-US',
                { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }
            );
        } catch {
            return val;
        }
    };

    return (
        <section
            data-testid="reception-next-visit-queue"
            aria-label={isAr ? 'طابور طلبات المتابعة السريرية' : 'Next-Visit Requests Queue'}
            className={`overflow-hidden rounded-2xl border border-border bg-surface-elevated transition-shadow sm:rounded-3xl ${className}`}
        >
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border p-4 sm:p-5">
                <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                        <Inbox size={20} aria-hidden="true" />
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <h3 className="text-base font-bold text-text-primary">
                                {isAr ? 'طلبات المتابعة السريرية' : 'Next-Visit Requests'}
                            </h3>
                            {pendingCount > 0 && (
                                <Badge
                                    variant="warning"
                                    size="xs"
                                    className="font-bold"
                                    data-testid="nvr-pending-badge"
                                >
                                    {pendingCount} {isAr ? 'بالانتظار' : 'pending'}
                                </Badge>
                            )}
                        </div>
                        <p className="text-xs text-text-secondary">
                            {isAr
                                ? 'طلبات المواعيد المحالة من العيادة وبانتظار التنسيق المكتبي'
                                : 'Chairside requests awaiting front-desk appointment booking'}
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    <div className="inline-flex rounded-xl border border-border bg-surface p-1 text-xs">
                        <button
                            type="button"
                            onClick={() => setStatusFilter('requested')}
                            className={`rounded-lg px-2.5 py-1 font-bold transition-colors ${
                                statusFilter === 'requested'
                                    ? 'bg-primary text-white shadow-low'
                                    : 'text-text-secondary hover:text-text-primary'
                            }`}
                            data-testid="nvr-filter-requested"
                        >
                            {isAr ? 'بالانتظار' : 'Pending'}
                        </button>
                        <button
                            type="button"
                            onClick={() => setStatusFilter('all')}
                            className={`rounded-lg px-2.5 py-1 font-bold transition-colors ${
                                statusFilter === 'all'
                                    ? 'bg-primary text-white shadow-low'
                                    : 'text-text-secondary hover:text-text-primary'
                            }`}
                            data-testid="nvr-filter-all"
                        >
                            {isAr ? 'الكل' : 'All'}
                        </button>
                    </div>

                    <button
                        type="button"
                        onClick={() => setIsCollapsed(!isCollapsed)}
                        className="inline-flex h-9 w-9 items-center justify-center rounded-xl text-text-secondary hover:bg-surface-hover hover:text-text-primary"
                        aria-label={isCollapsed ? (isAr ? 'توسيع القائمة' : 'Expand queue') : (isAr ? 'طي القائمة' : 'Collapse queue')}
                        aria-expanded={!isCollapsed}
                    >
                        {isCollapsed ? <ChevronDown size={18} /> : <ChevronUp size={18} />}
                    </button>
                </div>
            </div>

            {!isCollapsed && (
                <div className="p-4 sm:p-5">
                    {isLoading ? (
                        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                            <div className="h-28 animate-pulse rounded-2xl bg-surface" />
                            <div className="h-28 animate-pulse rounded-2xl bg-surface" />
                        </div>
                    ) : filteredRequests.length === 0 ? (
                        <EmptyState
                            title={isAr ? 'لا توجد طلبات متابعة معلقة' : 'No pending follow-up requests'}
                            description={
                                isAr
                                    ? 'عندما يحدد الطبيب موعد المتابعة أو مدته من كرسي العلاج ستظهر الطلبات هنا.'
                                    : 'When chairside clinicians queue next appointments, they will appear here for front-desk booking.'
                            }
                            icon={Calendar}
                        />
                    ) : (
                        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                            {filteredRequests.map((req) => (
                                <NextVisitCard
                                    key={req.id}
                                    request={req}
                                    isAr={isAr}
                                    formatDateTime={formatDateTime}
                                    onSchedule={onSchedule}
                                    onDismiss={onDismiss}
                                />
                            ))}
                        </div>
                    )}
                </div>
            )}
        </section>
    );
}

function NextVisitCard({ request, isAr, formatDateTime, onSchedule, onDismiss }) {
    const isPending = request.status === 'requested';
    const isScheduled = request.status === 'scheduled';

    const getStatusBadge = () => {
        switch (request.status) {
            case 'requested':
                return <Badge variant="warning" size="xs">{isAr ? 'مطلوب حجز' : 'Requested'}</Badge>;
            case 'scheduled':
                return <Badge variant="info" size="xs">{isAr ? 'مجدول' : 'Scheduled'}</Badge>;
            case 'completed':
                return <Badge variant="success" size="xs">{isAr ? 'مكتمل' : 'Completed'}</Badge>;
            case 'cancelled':
                return <Badge variant="default" size="xs">{isAr ? 'ملغي' : 'Cancelled'}</Badge>;
            default:
                return <Badge variant="default" size="xs">{request.status}</Badge>;
        }
    };

    return (
        <article
            data-testid={`next-visit-request-card-${request.id}`}
            className="flex flex-col justify-between rounded-2xl border border-border bg-surface p-4 shadow-sm transition hover:shadow-md"
        >
            <div className="space-y-2.5">
                <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-xs font-bold text-primary">
                            <User size={16} aria-hidden="true" />
                        </div>
                        <div className="min-w-0">
                            <h4 className="truncate text-sm font-bold text-text-primary" dir="auto">
                                {request.patient_name || (isAr ? 'مريض غير محدد' : 'Patient')}
                            </h4>
                            {request.patient_phone && (
                                <p className="flex items-center gap-1 text-[11px] text-text-secondary" dir="ltr">
                                    <Phone size={11} className="shrink-0" aria-hidden="true" />
                                    <span>{request.patient_phone}</span>
                                </p>
                            )}
                        </div>
                    </div>
                    {getStatusBadge()}
                </div>

                <div className="rounded-xl border border-border bg-surface-elevated p-2.5">
                    <p className="text-xs font-bold text-text-primary line-clamp-2" dir="auto">
                        {request.reason}
                    </p>
                    {request.notes && (
                        <p className="mt-1 text-[11px] text-text-secondary italic line-clamp-2" dir="auto">
                            {request.notes}
                        </p>
                    )}
                </div>

                <div className="flex flex-wrap items-center gap-2 text-xs text-text-secondary">
                    <span className="inline-flex items-center gap-1 rounded-lg bg-surface-hover px-2 py-0.5 font-bold">
                        <Clock size={12} className="text-primary" aria-hidden="true" />
                        {request.suggested_duration_minutes || 30} {isAr ? 'دقيقة' : 'min'}
                    </span>
                    {request.preferred_time_window_start && (
                        <span className="inline-flex items-center gap-1 text-[11px]">
                            <Calendar size={12} aria-hidden="true" />
                            {formatDateTime(request.preferred_time_window_start)}
                        </span>
                    )}
                </div>
            </div>

            <div className="mt-4 flex items-center justify-end gap-2 border-t border-border pt-3">
                {isPending ? (
                    <>
                        <Button
                            variant="ghost"
                            size="xs"
                            onClick={() => onDismiss && onDismiss(request)}
                            className="min-h-9 px-2.5 text-text-secondary hover:text-danger"
                            data-testid={`dismiss-request-btn-${request.id}`}
                            title={isAr ? 'إلغاء الطلب' : 'Dismiss request'}
                        >
                            <X size={15} className="me-1" aria-hidden="true" />
                            {isAr ? 'صرف' : 'Dismiss'}
                        </Button>
                        <Button
                            variant="primary"
                            size="xs"
                            onClick={() => onSchedule && onSchedule(request)}
                            className="min-h-9 px-3"
                            data-testid={`schedule-request-btn-${request.id}`}
                        >
                            <CalendarPlus size={15} className="me-1.5" aria-hidden="true" />
                            {isAr ? 'حجز الموعد' : 'Book Appointment'}
                        </Button>
                    </>
                ) : isScheduled && request.fulfilled_appointment_id ? (
                    <span className="text-[11px] font-bold text-primary">
                        {isAr ? `موعد رقم #${request.fulfilled_appointment_id}` : `Appt #${request.fulfilled_appointment_id}`}
                    </span>
                ) : null}
            </div>
        </article>
    );
}
