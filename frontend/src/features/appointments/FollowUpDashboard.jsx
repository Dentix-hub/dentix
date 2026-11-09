import { useState, useMemo } from 'react';
import PropTypes from 'prop-types';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
    CalendarClock,
    AlertTriangle,
    Clock,
    Calendar,
    User,
    Search,
    RefreshCw,
    Ban,
    ArrowRightLeft,
    Phone,
    X,
    Settings2,
} from 'lucide-react';
import { Button, SkeletonBox } from '@/shared/ui';
import { getFollowUpDashboard } from '@/api/appointments';
import { getDoctors } from '@/api/admin';
import FollowUpManagementModal from '@/features/care-sessions/FollowUpManagementModal';
import { useAuthStore } from '@/store/auth.store';

export default function FollowUpDashboard({ onSchedule }) {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const user = useAuthStore((state) => state.user);
    const role = String(user?.role || '').toLowerCase();
    let permissions = user?.permissions || [];
    if (typeof permissions === 'string') {
        try { permissions = JSON.parse(permissions); } catch { permissions = []; }
    }
    const hasPermission = (permission) => Array.isArray(permissions) && permissions.includes(permission);
    const canManage = ['admin', 'super_admin', 'doctor', 'nurse'].includes(role) || hasPermission('clinical:write');
    const canSchedule = ['admin', 'super_admin', 'doctor', 'receptionist', 'manager'].includes(role) || hasPermission('appointment:create');

    // Filters state
    const [search, setSearch] = useState('');
    const [dueCategory, setDueCategory] = useState('all'); // all, overdue, upcoming, unscheduled
    const [status, setStatus] = useState('all'); // all, requested, postponed, stopped, scheduled, completed
    const [doctorId, setDoctorId] = useState('');
    const [dateFrom, setDateFrom] = useState('');
    const [dateTo, setDateTo] = useState('');
    const [procedureCode, setProcedureCode] = useState('all');
    const [page, setPage] = useState(1);
    const pageSize = 20;
    const [managingRequest, setManagingRequest] = useState(null);

    // Fetch doctors
    const { data: doctors = [] } = useQuery({
        queryKey: ['doctors', 'follow-up-dashboard'],
        queryFn: async () => {
            const res = await getDoctors();
            const docs = res?.data?.doctors || res?.data || [];
            return Array.isArray(docs) ? docs : [];
        },
        staleTime: 5 * 60 * 1000,
    });

    // Query parameters
    const queryParams = useMemo(() => {
        const p = {
            skip: (page - 1) * pageSize,
            limit: pageSize,
        };
        if (search.trim()) p.search = search.trim();
        if (dueCategory && dueCategory !== 'all') p.due_category = dueCategory;
        if (status && status !== 'all') p.status = status;
        if (doctorId) p.doctor_id = Number(doctorId);
        if (procedureCode && procedureCode !== 'all') p.procedure_code = procedureCode;
        // Calendar dates belong to the clinic timezone, resolved by the server.
        if (dateFrom) p.calendar_date_from = dateFrom;
        if (dateTo) p.calendar_date_to = dateTo;
        return p;
    }, [search, dueCategory, status, doctorId, procedureCode, dateFrom, dateTo, page, pageSize]);

    // Fetch Dashboard data
    const {
        data: response,
        isLoading,
        isFetching,
        refetch,
    } = useQuery({
        queryKey: ['follow-up-dashboard', queryParams],
        queryFn: async () => {
            const res = await getFollowUpDashboard(queryParams);
            return res?.data?.data || res?.data || { counts: {}, items: [], total: 0 };
        },
    });

    const counts = response?.counts || {};
    const items = response?.items || [];
    const totalCount = response?.total_count ?? response?.total ?? items.length;
    const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

    const handleClearFilters = () => {
        setSearch('');
        setDueCategory('all');
        setStatus('all');
        setDoctorId('');
        setProcedureCode('all');
        setDateFrom('');
        setDateTo('');
        setPage(1);
    };

    const hasActiveFilters = Boolean(
        search.trim() ||
        (dueCategory && dueCategory !== 'all') ||
        (status && status !== 'all') ||
        doctorId ||
        (procedureCode && procedureCode !== 'all') ||
        dateFrom ||
        dateTo
    );

    const formatTargetDate = (item) => {
        const d = item.target_date || item.postponed_to_date || item.preferred_time_window_start;
        if (!d) return t('follow_up.unscheduled', 'Unscheduled');
        try {
            const dateObj = new Date(d);
            const now = new Date();
            const diffDays = Math.round((dateObj - now) / (1000 * 60 * 60 * 24));

            let relative = '';
            if (diffDays < 0) {
                relative = `(${Math.abs(diffDays)}d overdue)`;
            } else if (diffDays === 0) {
                relative = '(Today)';
            } else {
                relative = `(in ${diffDays}d)`;
            }

            return `${dateObj.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })} ${relative}`;
        } catch {
            return String(d);
        }
    };

    const getDueBadge = (cat) => {
        switch (cat) {
            case 'overdue':
                return (
                    <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-bold text-red-800 dark:bg-red-950/60 dark:text-red-300">
                        <AlertTriangle className="h-3 w-3" />
                        {t('follow_up.overdue', 'Overdue')}
                    </span>
                );
            case 'upcoming':
                return (
                    <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-bold text-blue-800 dark:bg-blue-950/60 dark:text-blue-300">
                        <Clock className="h-3 w-3" />
                        {t('follow_up.upcoming', 'Upcoming')}
                    </span>
                );
            case 'scheduled':
            case 'completed':
            case 'cancelled':
            case 'stopped':
                return getStatusBadge(cat);
            case 'unscheduled':
            default:
                return (
                    <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                        {t('follow_up.unscheduled', 'Unscheduled')}
                    </span>
                );
        }
    };

    const getStatusBadge = (st) => {
        switch (st) {
            case 'requested':
                return <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-bold text-amber-800 dark:bg-amber-950 dark:text-amber-300">Requested</span>;
            case 'scheduled':
                return <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-bold text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">Scheduled</span>;
            case 'postponed':
                return <span className="rounded-full bg-orange-100 px-2 py-0.5 text-[11px] font-bold text-orange-800 dark:bg-orange-950 dark:text-orange-300">Postponed</span>;
            case 'stopped':
                return <span className="rounded-full bg-slate-200 px-2 py-0.5 text-[11px] font-bold text-slate-700 dark:bg-slate-700 dark:text-slate-300">Stopped</span>;
            case 'completed':
                return <span className="rounded-full bg-teal-100 px-2 py-0.5 text-[11px] font-bold text-teal-800 dark:bg-teal-950 dark:text-teal-300">Completed</span>;
            default:
                return <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">{st}</span>;
        }
    };

    return (
        <div data-testid="follow-up-dashboard" className="space-y-6 animate-in fade-in duration-300">
            {/* Header & Refresh */}
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                    <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                        <CalendarClock className="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
                        <span>{t('follow_up.dashboard_title', 'Follow-Up & Clinical Recall Dashboard')}</span>
                    </h2>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                        {t('follow_up.dashboard_subtitle', 'Monitor patient recalls, overdue treatment follow-ups, and clinic-wide return visits.')}
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => refetch()}
                        disabled={isFetching}
                        className="text-xs font-semibold"
                        data-testid="refresh-dashboard-btn"
                    >
                        <RefreshCw className={`h-3.5 w-3.5 me-1.5 ${isFetching ? 'animate-spin' : ''}`} />
                        <span>{t('common.refresh', 'Refresh')}</span>
                    </Button>
                </div>
            </div>

            {/* Metric KPI Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3" data-testid="kpi-cards">
                {/* Total */}
                <div className="rounded-2xl border border-slate-200 bg-white p-3.5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                        {t('follow_up.kpi_total', 'Total Recalls')}
                    </span>
                    <div className="mt-1 text-2xl font-black text-slate-900 dark:text-white">
                        {isLoading ? '--' : counts.total || 0}
                    </div>
                </div>

                {/* Overdue */}
                <div
                    onClick={() => setDueCategory(dueCategory === 'overdue' ? 'all' : 'overdue')}
                    className={`cursor-pointer rounded-2xl border p-3.5 transition-all shadow-xs ${
                        dueCategory === 'overdue'
                            ? 'border-red-500 bg-red-50/80 dark:border-red-600 dark:bg-red-950/40 ring-2 ring-red-500'
                            : 'border-red-200 bg-red-50/30 hover:bg-red-50 dark:border-red-900/40 dark:bg-red-950/10'
                    }`}
                >
                    <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-red-700 dark:text-red-400">
                            {t('follow_up.kpi_overdue', 'Overdue')}
                        </span>
                        <AlertTriangle className="h-4 w-4 text-red-600" />
                    </div>
                    <div className="mt-1 text-2xl font-black text-red-700 dark:text-red-400">
                        {isLoading ? '--' : counts.overdue || 0}
                    </div>
                </div>

                {/* Upcoming */}
                <div
                    onClick={() => setDueCategory(dueCategory === 'upcoming' ? 'all' : 'upcoming')}
                    className={`cursor-pointer rounded-2xl border p-3.5 transition-all shadow-xs ${
                        dueCategory === 'upcoming'
                            ? 'border-blue-500 bg-blue-50/80 dark:border-blue-600 dark:bg-blue-950/40 ring-2 ring-blue-500'
                            : 'border-blue-200 bg-blue-50/30 hover:bg-blue-50 dark:border-blue-900/40 dark:bg-blue-950/10'
                    }`}
                >
                    <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-blue-700 dark:text-blue-400">
                            {t('follow_up.kpi_upcoming', 'Upcoming')}
                        </span>
                        <Clock className="h-4 w-4 text-blue-600" />
                    </div>
                    <div className="mt-1 text-2xl font-black text-blue-700 dark:text-blue-400">
                        {isLoading ? '--' : counts.upcoming || 0}
                    </div>
                </div>

                {/* Unscheduled */}
                <div
                    onClick={() => setDueCategory(dueCategory === 'unscheduled' ? 'all' : 'unscheduled')}
                    className={`cursor-pointer rounded-2xl border p-3.5 transition-all shadow-xs ${
                        dueCategory === 'unscheduled'
                            ? 'border-purple-500 bg-purple-50/80 dark:border-purple-600 dark:bg-purple-950/40 ring-2 ring-purple-500'
                            : 'border-purple-200 bg-purple-50/30 hover:bg-purple-50 dark:border-purple-900/40 dark:bg-purple-950/10'
                    }`}
                >
                    <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-purple-700 dark:text-purple-400">
                            {t('follow_up.kpi_unscheduled', 'Unscheduled')}
                        </span>
                        <CalendarClock className="h-4 w-4 text-purple-600" />
                    </div>
                    <div className="mt-1 text-2xl font-black text-purple-700 dark:text-purple-400">
                        {isLoading ? '--' : counts.unscheduled || 0}
                    </div>
                </div>

                {/* Postponed */}
                <div
                    onClick={() => setStatus(status === 'postponed' ? 'all' : 'postponed')}
                    className={`cursor-pointer rounded-2xl border p-3.5 transition-all shadow-xs ${
                        status === 'postponed'
                            ? 'border-orange-500 bg-orange-50/80 dark:border-orange-600 dark:bg-orange-950/40 ring-2 ring-orange-500'
                            : 'border-orange-200 bg-orange-50/30 hover:bg-orange-50 dark:border-orange-900/40 dark:bg-orange-950/10'
                    }`}
                >
                    <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-orange-700 dark:text-orange-400">
                            {t('follow_up.kpi_postponed', 'Postponed')}
                        </span>
                        <ArrowRightLeft className="h-4 w-4 text-orange-600" />
                    </div>
                    <div className="mt-1 text-2xl font-black text-orange-700 dark:text-orange-400">
                        {isLoading ? '--' : counts.postponed || 0}
                    </div>
                </div>

                {/* Stopped */}
                <div
                    onClick={() => setStatus(status === 'stopped' ? 'all' : 'stopped')}
                    className={`cursor-pointer rounded-2xl border p-3.5 transition-all shadow-xs ${
                        status === 'stopped'
                            ? 'border-slate-500 bg-slate-100 dark:border-slate-600 dark:bg-slate-800 ring-2 ring-slate-500'
                            : 'border-slate-200 bg-slate-50/40 hover:bg-slate-100/50 dark:border-slate-800 dark:bg-slate-900'
                    }`}
                >
                    <div className="flex items-center justify-between">
                        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">
                            {t('follow_up.kpi_stopped', 'Stopped')}
                        </span>
                        <Ban className="h-4 w-4 text-slate-500" />
                    </div>
                    <div className="mt-1 text-2xl font-bold text-slate-700 dark:text-slate-300">
                        {isLoading ? '--' : counts.stopped || 0}
                    </div>
                </div>
            </div>

            {/* Filter Controls Bar */}
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs dark:border-slate-800 dark:bg-slate-900 space-y-3">
                <div className="flex flex-wrap items-center gap-3">
                    {/* Search */}
                    <div className="relative flex-1 min-w-[220px]">
                        <Search className="absolute start-3 top-2.5 h-4 w-4 text-slate-400" />
                        <input
                            type="text"
                            data-testid="search-input"
                            value={search}
                            onChange={(e) => {
                                setSearch(e.target.value);
                                setPage(1);
                            }}
                            placeholder={t('follow_up.search_placeholder', 'Search patient name, phone, or clinical reason...')}
                            className="w-full rounded-xl border border-slate-200 bg-slate-50/60 py-2 ps-9 pe-3 text-xs focus:border-primary focus:bg-white focus:outline-none focus:ring-1 focus:ring-primary dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                        />
                        {search && (
                            <button
                                type="button"
                                onClick={() => {
                                    setSearch('');
                                    setPage(1);
                                }}
                                className="absolute end-2.5 top-2.5 text-slate-400 hover:text-slate-600"
                            >
                                <X className="h-3.5 w-3.5" />
                            </button>
                        )}
                    </div>

                    {/* Status Dropdown */}
                    <div className="min-w-[130px]">
                        <select
                            data-testid="status-select"
                            value={status}
                            onChange={(e) => {
                                setStatus(e.target.value);
                                setPage(1);
                            }}
                            className="w-full rounded-xl border border-slate-200 bg-white py-2 px-3 text-xs font-medium text-slate-700 focus:border-primary focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                        >
                            <option value="all">{t('common.all_statuses', 'All Statuses')}</option>
                            <option value="requested">Requested</option>
                            <option value="scheduled">Scheduled</option>
                            <option value="postponed">Postponed</option>
                            <option value="stopped">Stopped</option>
                            <option value="completed">Completed</option>
                            <option value="cancelled">Cancelled</option>
                        </select>
                    </div>

                    {/* Doctor Dropdown */}
                    <div className="min-w-[140px]">
                        <select
                            data-testid="doctor-select"
                            value={doctorId}
                            onChange={(e) => {
                                setDoctorId(e.target.value);
                                setPage(1);
                            }}
                            className="w-full rounded-xl border border-slate-200 bg-white py-2 px-3 text-xs font-medium text-slate-700 focus:border-primary focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                        >
                            <option value="">{t('common.all_doctors', 'All Doctors')}</option>
                            {doctors.map((doc) => (
                                <option key={doc.id} value={doc.id}>
                                    {doc.full_name || doc.name || `Dr. #${doc.id}`}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Procedure Filter */}
                    <div className="min-w-[140px]">
                        <select
                            data-testid="select-filter-procedure"
                            value={procedureCode}
                            onChange={(e) => {
                                setProcedureCode(e.target.value);
                                setPage(1);
                            }}
                            className="w-full rounded-xl border border-slate-200 bg-white py-2 px-3 text-xs font-medium text-slate-700 focus:border-primary focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                        >
                            <option value="all">{t('common.all_procedures', 'All Procedures')}</option>
                            <option value="ENDO_RCT">Endodontics (RCT)</option>
                            <option value="PROS_CROWN">Crown</option>
                            <option value="PROS_BRIDGE">Bridge</option>
                            <option value="REST_COMPOSITE">Composite Restoration</option>
                            <option value="SURG_EXTRACTION">Extraction</option>
                            <option value="PROS_DENTURE">Denture</option>
                        </select>
                    </div>

                    {/* Date Range Pickers */}
                    <div className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-400">
                        <input
                            type="date"
                            data-testid="input-filter-date-from"
                            value={dateFrom}
                            onChange={(e) => {
                                setDateFrom(e.target.value);
                                setPage(1);
                            }}
                            title={t('common.date_from', 'Date from')}
                            className="rounded-xl border border-slate-200 bg-white py-1.5 px-2.5 text-xs text-slate-700 focus:border-primary focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                        />
                        <span>-</span>
                        <input
                            type="date"
                            data-testid="input-filter-date-to"
                            value={dateTo}
                            onChange={(e) => {
                                setDateTo(e.target.value);
                                setPage(1);
                            }}
                            title={t('common.date_to', 'Date to')}
                            className="rounded-xl border border-slate-200 bg-white py-1.5 px-2.5 text-xs text-slate-700 focus:border-primary focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                        />
                    </div>

                    {/* Due Category Filter Pills */}
                    <div className="flex items-center rounded-xl border border-slate-200 bg-slate-50 p-1 text-xs font-semibold dark:border-slate-700 dark:bg-slate-800">
                        {['all', 'overdue', 'upcoming', 'unscheduled'].map((cat) => (
                            <button
                                key={cat}
                                type="button"
                                data-testid={`filter-cat-${cat}`}
                                onClick={() => {
                                    setDueCategory(cat);
                                    setPage(1);
                                }}
                                className={`rounded-lg px-2.5 py-1 capitalize transition-colors ${
                                    dueCategory === cat
                                        ? 'bg-white text-indigo-700 shadow-xs dark:bg-slate-700 dark:text-white'
                                        : 'text-slate-600 hover:text-slate-900 dark:text-slate-400'
                                }`}
                            >
                                {cat}
                            </button>
                        ))}
                    </div>

                    {/* Clear Filters */}
                    {hasActiveFilters && (
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={handleClearFilters}
                            className="text-xs text-slate-500 hover:text-slate-800"
                        >
                            <X className="h-3.5 w-3.5 me-1" />
                            <span>{t('common.clear', 'Clear')}</span>
                        </Button>
                    )}
                </div>
            </div>

            {/* Requests Table / Cards */}
            <div className="rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden dark:border-slate-800 dark:bg-slate-900">
                {isLoading ? (
                    <div className="p-6 space-y-3">
                        <SkeletonBox className="h-12 w-full rounded-xl" />
                        <SkeletonBox className="h-12 w-full rounded-xl" />
                        <SkeletonBox className="h-12 w-full rounded-xl" />
                    </div>
                ) : items.length === 0 ? (
                    <div className="p-12 text-center text-slate-500 dark:text-slate-400" data-testid="empty-requests">
                        <CalendarClock className="h-10 w-10 mx-auto text-slate-300 dark:text-slate-600 mb-3" />
                        <h4 className="font-bold text-slate-800 dark:text-slate-200 text-sm">
                            {t('follow_up.no_requests_found', 'No follow-up requests match your filters')}
                        </h4>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                            {hasActiveFilters
                                ? t('follow_up.try_clearing_filters', 'Try resetting filters or adjusting search parameters.')
                                : t('follow_up.no_pending_requests', 'No return visit requests currently recorded.')}
                        </p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-start align-middle" data-testid="follow-ups-table">
                            <thead className="bg-slate-50 text-slate-600 text-xs font-bold uppercase tracking-wider dark:bg-slate-800/60 dark:text-slate-400 border-b border-slate-100 dark:border-slate-800">
                                <tr>
                                    <th className="p-3.5 whitespace-nowrap">{t('follow_up.patient', 'Patient')}</th>
                                    <th className="p-3.5 whitespace-nowrap">{t('follow_up.procedure', 'Procedure / Tooth')}</th>
                                    <th className="p-3.5 whitespace-nowrap min-w-[200px]">{t('follow_up.reason', 'Next Action & Clinical Goal')}</th>
                                    <th className="p-3.5 whitespace-nowrap">{t('follow_up.due_date', 'Due / Target')}</th>
                                    <th className="p-3.5 whitespace-nowrap">{t('follow_up.doctor', 'Assigned Doctor')}</th>
                                    <th className="p-3.5 whitespace-nowrap">{t('follow_up.status', 'Status')}</th>
                                    <th className="p-3.5 whitespace-nowrap text-end">{t('follow_up.actions', 'Actions')}</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-xs">
                                {items.map((req) => (
                                    <tr
                                        key={req.id}
                                        data-testid={`follow-up-row-${req.id}`}
                                        className="hover:bg-slate-50/70 transition-colors dark:hover:bg-slate-800/40"
                                    >
                                        {/* Patient */}
                                        <td className="p-3.5 whitespace-nowrap">
                                            <div>
                                                <Link
                                                    to={`/patients/${req.patient_id}`}
                                                    className="font-bold text-slate-900 hover:text-primary dark:text-slate-100 dark:hover:text-primary"
                                                >
                                                    {req.patient_name || `Patient #${req.patient_id}`}
                                                </Link>
                                                {req.patient_phone && (
                                                    <div className="flex items-center gap-1 text-[11px] text-slate-500 font-mono mt-0.5">
                                                        <Phone className="h-3 w-3" />
                                                        <span>{req.patient_phone}</span>
                                                    </div>
                                                )}
                                            </div>
                                        </td>

                                        {/* Procedure */}
                                        <td className="p-3.5 whitespace-nowrap">
                                            <span className="font-semibold text-slate-800 dark:text-slate-200">
                                                {req.procedure_name || 'Clinical Care'}
                                            </span>
                                            {req.tooth_number && (
                                                <span className="ms-1.5 rounded bg-slate-100 px-1.5 py-0.2 font-mono text-[10px] font-bold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                                                    Tooth #{req.tooth_number}
                                                </span>
                                            )}
                                        </td>

                                        {/* Reason & Duration */}
                                        <td className="p-3.5">
                                            <div className="font-semibold text-slate-900 dark:text-slate-100">
                                                {req.reason}
                                            </div>
                                            {req.suggested_duration_minutes && (
                                                <span className="text-[11px] text-slate-500 flex items-center gap-1 mt-0.5">
                                                    <Clock className="h-3 w-3" />
                                                    <span>{req.suggested_duration_minutes} min duration</span>
                                                </span>
                                            )}
                                        </td>

                                        {/* Due / Target Date & Due Category */}
                                        <td className="p-3.5 whitespace-nowrap">
                                            <div className="flex flex-col gap-1">
                                                {getDueBadge(req.due_category)}
                                                <span className="text-[11px] text-slate-600 dark:text-slate-400 font-medium">
                                                    {formatTargetDate(req)}
                                                </span>
                                            </div>
                                        </td>

                                        {/* Assigned Doctor */}
                                        <td className="p-3.5 whitespace-nowrap">
                                            <span className="flex items-center gap-1.5 text-slate-700 dark:text-slate-300 font-medium">
                                                <User className="h-3.5 w-3.5 text-slate-400" />
                                                <span>{req.assigned_doctor_name || t('common.unassigned', 'Unassigned')}</span>
                                            </span>
                                        </td>

                                        {/* Status */}
                                        <td className="p-3.5 whitespace-nowrap">
                                            {getStatusBadge(req.status)}
                                        </td>

                                        {/* Actions */}
                                        <td className="p-3.5 whitespace-nowrap text-end">
                                            <div className="flex items-center justify-end gap-2">
                                                {/* Schedule Button */}
                                                {canSchedule && onSchedule && req.status === 'requested' && (
                                                    <Button
                                                        variant="primary"
                                                        size="xs"
                                                        data-testid={`schedule-btn-${req.id}`}
                                                        onClick={() => onSchedule && onSchedule(req)}
                                                        className="font-bold"
                                                    >
                                                        <Calendar className="h-3 w-3 me-1" />
                                                        <span>{t('follow_up.schedule', 'Schedule')}</span>
                                                    </Button>
                                                )}

                                                {/* Manage Actions Modal */}
                                                {canManage && <Button
                                                    variant="ghost"
                                                    size="xs"
                                                    data-testid={`manage-request-btn-${req.id}`}
                                                    onClick={() => setManagingRequest(req)}
                                                    className="text-slate-600 hover:text-indigo-600"
                                                    title={t('common.manage', 'Manage')}
                                                >
                                                    <Settings2 className="h-3.5 w-3.5 me-1" />
                                                    <span>{t('common.manage', 'Manage')}</span>
                                                </Button>}
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {/* Pagination Controls */}
                {totalCount > 0 && (
                    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 px-4 py-3 bg-slate-50/50 dark:border-slate-800 dark:bg-slate-900/50">
                        <span className="text-xs text-slate-500">
                            {t('common.showing_results', `Showing ${Math.min((page - 1) * pageSize + 1, totalCount)} to ${Math.min(page * pageSize, totalCount)} of ${totalCount} follow-ups`)}
                        </span>
                        <div className="flex items-center gap-2">
                            <Button
                                variant="outline"
                                size="xs"
                                data-testid="btn-prev-page"
                                disabled={page <= 1 || isLoading}
                                onClick={() => setPage((p) => Math.max(1, p - 1))}
                            >
                                {t('common.previous', 'Previous')}
                            </Button>
                            <span data-testid="page-indicator" className="text-xs font-semibold text-slate-700 dark:text-slate-300 px-2">
                                {page} / {totalPages}
                            </span>
                            <Button
                                variant="outline"
                                size="xs"
                                data-testid="btn-next-page"
                                disabled={page >= totalPages || isLoading}
                                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                            >
                                {t('common.next', 'Next')}
                            </Button>
                        </div>
                    </div>
                )}
            </div>

            {/* Follow-Up Management Modal */}
            {canManage && managingRequest && (
                <FollowUpManagementModal
                    isOpen={Boolean(managingRequest)}
                    request={managingRequest}
                    doctors={doctors}
                    onClose={() => setManagingRequest(null)}
                    onSuccess={() => {
                        queryClient.invalidateQueries({ queryKey: ['follow-up-dashboard'] });
                        setManagingRequest(null);
                    }}
                />
            )}
        </div>
    );
}

FollowUpDashboard.propTypes = {
    onSchedule: PropTypes.func,
};
