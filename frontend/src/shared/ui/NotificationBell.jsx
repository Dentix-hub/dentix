import { useCallback, useEffect, useRef, useState } from 'react';
import logger from '@/utils/logger';
import { Bell, Info, AlertTriangle, CheckCircle, XCircle, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { getNotifications, markNotificationRead, dismissNotification } from '@/api';
import { useAuth } from '@/auth/useAuth';
import DentixBottomSheet from '@/shared/ui/DentixBottomSheet';

const NOTIFICATION_TYPES = {
    WARNING: 'warning',
    SUCCESS: 'success',
    ERROR: 'error',
    INFO: 'info'
};

const POLL_INTERVAL_MS = 120000;

function useCompactViewport() {
    const getMatch = () => typeof window !== 'undefined' && window.matchMedia('(max-width: 639px)').matches;
    const [isCompact, setIsCompact] = useState(getMatch);

    useEffect(() => {
        if (typeof window === 'undefined') return undefined;
        const media = window.matchMedia('(max-width: 639px)');
        const onChange = (event) => setIsCompact(event.matches);
        setIsCompact(media.matches);
        media.addEventListener?.('change', onChange);
        return () => media.removeEventListener?.('change', onChange);
    }, []);

    return isCompact;
}

const NotificationBell = () => {
    const { user } = useAuth();
    const { t } = useTranslation();
    const [notifications, setNotifications] = useState([]);
    const [showDropdown, setShowDropdown] = useState(false);
    const [unreadCount, setUnreadCount] = useState(0);
    const dropdownRef = useRef(null);
    const isCompact = useCompactViewport();

    const fetchNotifications = useCallback(async () => {
        if (!user) return;
        try {
            const response = await getNotifications();
            if (response?.data && Array.isArray(response.data)) {
                setNotifications(response.data);
                setUnreadCount(response.data.filter(n => !n.is_read).length);
            } else if (response?.data && Array.isArray(response.data.notifications)) {
                setNotifications(response.data.notifications);
                setUnreadCount(response.data.notifications.filter(n => !n.is_read).length);
            }
        } catch (error) {
            if (error.response?.status !== 401) {
                logger.error('Failed to sync notifications:', error);
            }
        }
    }, [user]);

    useEffect(() => {
        if (user) {
            fetchNotifications();
            const interval = setInterval(fetchNotifications, POLL_INTERVAL_MS);
            return () => clearInterval(interval);
        }
        setNotifications([]);
        setUnreadCount(0);
        return undefined;
    }, [fetchNotifications, user]);

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (!isCompact && dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setShowDropdown(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [isCompact]);

    const handleMarkAsRead = async (id) => {
        try {
            await markNotificationRead(id);
            setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
            setUnreadCount(prev => Math.max(0, prev - 1));
        } catch (error) {
            logger.error('Error marking notification as read:', error);
        }
    };

    const handleDismiss = async (id) => {
        try {
            setNotifications(prev => prev.filter(n => n.id !== id));
            setUnreadCount(prev => {
                const wasUnread = notifications.find(n => n.id === id && !n.is_read);
                return wasUnread ? Math.max(0, prev - 1) : prev;
            });
            await dismissNotification(id);
        } catch (error) {
            logger.error('Error dismissing notification:', error);
            fetchNotifications();
        }
    };

    const getIcon = (type) => {
        switch (type) {
            case NOTIFICATION_TYPES.WARNING: return <AlertTriangle className="h-4 w-4 text-amber-500" aria-hidden="true" />;
            case NOTIFICATION_TYPES.SUCCESS: return <CheckCircle className="h-4 w-4 text-emerald-500" aria-hidden="true" />;
            case NOTIFICATION_TYPES.ERROR: return <XCircle className="h-4 w-4 text-rose-500" aria-hidden="true" />;
            default: return <Info className="h-4 w-4 text-blue-500" aria-hidden="true" />;
        }
    };

    const renderNotifications = () => (
        <div className="min-w-0 overflow-y-auto overscroll-contain">
            {notifications.length === 0 ? (
                <div className="px-4 py-8 text-center text-slate-500">
                    <Bell className="mx-auto mb-2 h-8 w-8 opacity-20" aria-hidden="true" />
                    <p className="text-sm">{t('notifications.empty', 'No new notifications')}</p>
                </div>
            ) : (
                notifications.map((notification) => (
                    <div
                        key={notification.id}
                        className={`flex min-w-0 items-start gap-2 border-s-4 px-2 py-2 transition-colors sm:px-3 ${notification.is_read ? 'border-transparent bg-white dark:bg-slate-900' : 'border-blue-500 bg-blue-50/30 dark:bg-blue-950/20'}`}
                    >
                        <button
                            type="button"
                            onClick={() => !notification.is_read && handleMarkAsRead(notification.id)}
                            className="flex min-h-11 min-w-0 flex-1 items-start gap-3 rounded-xl p-2 text-start transition-colors hover:bg-slate-50 dark:hover:bg-white/5"
                            aria-label={notification.is_read ? notification.title : t('notifications.mark_read', `Mark ${notification.title} as read`)}
                        >
                            <span className="mt-1 shrink-0">{getIcon(notification.type)}</span>
                            <span className="min-w-0 flex-1">
                                <span className="flex min-w-0 flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
                                    <span className={`min-w-0 break-words text-sm font-semibold ${notification.is_read ? 'text-slate-700 dark:text-slate-300' : 'text-slate-900 dark:text-white'}`}>
                                        {notification.title}
                                    </span>
                                    <span className="shrink-0 text-[10px] text-slate-500">
                                        {new Date(notification.created_at).toLocaleDateString()}
                                    </span>
                                </span>
                                <span className="mt-1 block break-words text-xs text-slate-500 dark:text-slate-400">
                                    {notification.content}
                                </span>
                            </span>
                        </button>
                        <button
                            type="button"
                            onClick={() => handleDismiss(notification.id)}
                            className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-slate-400 transition-colors hover:bg-rose-50 hover:text-rose-500 dark:hover:bg-rose-950/30"
                            title={t('notifications.dismiss', 'Dismiss notification')}
                            aria-label={t('notifications.dismiss', 'Dismiss notification')}
                        >
                            <Trash2 size={16} aria-hidden="true" />
                        </button>
                    </div>
                ))
            )}
        </div>
    );

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                type="button"
                onClick={() => setShowDropdown(prev => !prev)}
                className="relative inline-flex h-11 w-11 items-center justify-center rounded-xl text-slate-600 transition-colors hover:bg-blue-50 hover:text-blue-600 dark:text-slate-300 dark:hover:bg-blue-950/30"
                aria-label={t('notifications.title', 'Notifications')}
                aria-expanded={showDropdown}
            >
                <Bell size={22} aria-hidden="true" />
                {unreadCount > 0 && (
                    <span className="absolute end-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full border-2 border-white bg-rose-500 px-0.5 text-[9px] font-bold text-white dark:border-slate-900">
                        {unreadCount > 9 ? '9+' : unreadCount}
                    </span>
                )}
            </button>

            {!isCompact && showDropdown && (
                <div className="absolute end-0 z-50 mt-2 flex max-h-[min(450px,calc(100dvh-5rem))] w-[min(22rem,calc(100vw-2rem))] flex-col overflow-hidden rounded-xl border border-border bg-surface-elevated py-2 shadow-xl">
                    <div className="flex items-center justify-between border-b border-border px-4 py-2">
                        <h3 className="font-bold text-text-primary">{t('notifications.title', 'Notifications')}</h3>
                        {unreadCount > 0 && <span className="text-xs font-medium text-blue-600">{unreadCount} {t('notifications.new', 'new')}</span>}
                    </div>
                    {renderNotifications()}
                </div>
            )}

            {isCompact && (
                <DentixBottomSheet
                    open={showDropdown}
                    onOpenChange={setShowDropdown}
                    title={t('notifications.title', 'Notifications')}
                    closeLabel={t('common.close', 'Close')}
                >
                    {unreadCount > 0 && (
                        <p className="mb-2 text-xs font-medium text-blue-600">{unreadCount} {t('notifications.new', 'new')}</p>
                    )}
                    <div className="overflow-hidden rounded-2xl border border-border">
                        {renderNotifications()}
                    </div>
                </DentixBottomSheet>
            )}
        </div>
    );
};

export default NotificationBell;
