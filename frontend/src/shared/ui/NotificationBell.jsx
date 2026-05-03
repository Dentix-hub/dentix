import { useState, useEffect, useRef } from 'react';
import { Bell, Info, AlertTriangle, CheckCircle, XCircle, Trash2 } from 'lucide-react';
import { getNotifications, markNotificationRead, dismissNotification } from '@/api';
import { useAuth } from '@/auth/useAuth';

const NOTIFICATION_TYPES = {
    WARNING: 'warning',
    SUCCESS: 'success',
    ERROR: 'error',
    INFO: 'info'
};

const POLL_INTERVAL_MS = 120000; // 2 Minutes

const NotificationBell = () => {
    const { user } = useAuth();
    const [notifications, setNotifications] = useState([]);
    const [showDropdown, setShowDropdown] = useState(false);
    const [unreadCount, setUnreadCount] = useState(0);
    const dropdownRef = useRef(null);

    const fetchNotifications = async () => {
        if (!user) return;
        try {
            const response = await getNotifications();
            if (response?.data && Array.isArray(response.data)) {
                setNotifications(response.data);
                setUnreadCount(response.data.filter(n => !n.is_read).length);
            } else if (response?.data && Array.isArray(response.data.notifications)) {
                // Support potential wrapped format
                setNotifications(response.data.notifications);
                setUnreadCount(response.data.notifications.filter(n => !n.is_read).length);
            }
        } catch (error) {
            if (error.response?.status !== 401) {
                console.error('Failed to sync notifications:', error);
            }
        }
    };

    useEffect(() => {
        if (user) {
            fetchNotifications();
            const interval = setInterval(fetchNotifications, POLL_INTERVAL_MS);
            return () => clearInterval(interval);
        } else {
            setNotifications([]);
            setUnreadCount(0);
        }
    }, [user]);

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setShowDropdown(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);
    const handleMarkAsRead = async (id) => {
        try {
            await markNotificationRead(id);
            setNotifications(prev => prev.map(n =>
                n.id === id ? { ...n, is_read: true } : n
            ));
            setUnreadCount(prev => Math.max(0, prev - 1));
        } catch (error) {
            console.error('Error marking notification as read:', error);
        }
    };
    const handleDismiss = async (id) => {
        try {
            // Optimistic Update
            setNotifications(prev => prev.filter(n => n.id !== id));
            // Update unread count if we just deleted an unread one
            setUnreadCount(prev => {
                const wasUnread = notifications.find(n => n.id === id && !n.is_read);
                return wasUnread ? Math.max(0, prev - 1) : prev;
            });
            await dismissNotification(id);
        } catch (error) {
            console.error('Error dismissing notification:', error);
            fetchNotifications(); // Revert on error
        }
    };
    const getIcon = (type) => {
        switch (type) {
            case NOTIFICATION_TYPES.WARNING: return <AlertTriangle className="w-4 h-4 text-amber-500" />;
            case NOTIFICATION_TYPES.SUCCESS: return <CheckCircle className="w-4 h-4 text-emerald-500" />;
            case NOTIFICATION_TYPES.ERROR: return <XCircle className="w-4 h-4 text-rose-500" />;
            default: return <Info className="w-4 h-4 text-blue-500" />;
        }
    };
    return (
        <div className="relative" ref={dropdownRef}>
            <button
                onClick={() => setShowDropdown(!showDropdown)}
                className="p-2 text-slate-600 hover:text-blue-600 hover:bg-blue-50 rounded-full transition-all relative"
                aria-label="Notifications"
            >
                <Bell size={22} />
                {unreadCount > 0 && (
                    <span className="absolute top-1.5 right-1.5 w-4 h-4 bg-rose-500 text-white text-[10px] font-bold flex items-center justify-center rounded-full border-2 border-white">
                        {unreadCount > 9 ? '9+' : unreadCount}
                    </span>
                )}
            </button>
            {showDropdown && (
                <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-xl border border-slate-100 py-2 z-50 overflow-hidden max-h-[450px] flex flex-col">
                    <div className="px-4 py-2 border-b border-slate-50 flex justify-between items-center">
                        <h3 className="font-bold text-slate-800">الإشعارات</h3>
                        {unreadCount > 0 && <span className="text-xs text-blue-600 font-medium">{unreadCount} جديد</span>}
                    </div>
                    <div className="overflow-y-auto">
                        {notifications.length === 0 ? (
                            <div className="px-4 py-8 text-center text-slate-400">
                                <Bell className="w-8 h-8 mx-auto mb-2 opacity-20" />
                                <p className="text-sm">لا توجد إشعارات جديدة</p>
                            </div>
                        ) : (
                            notifications.map((notification) => (
                                <div
                                    key={notification.id}
                                    className={`px-4 py-3 hover:bg-slate-50 transition-colors cursor-pointer border-l-4 ${notification.is_read ? 'border-transparent bg-white' : 'border-blue-500 bg-blue-50/30'}`}
                                    onClick={() => !notification.is_read && handleMarkAsRead(notification.id)}
                                >
                                    <div className="flex gap-3 relative group">
                                        <div className="mt-1">{getIcon(notification.type)}</div>
                                        <div className="flex-1">
                                            <div className="flex justify-between items-start">
                                                <h4 className={`text-sm font-semibold ${notification.is_read ? 'text-slate-700' : 'text-slate-900'}`}>
                                                    {notification.title}
                                                </h4>
                                                <div className="flex items-center gap-2">
                                                    <span className="text-[10px] text-slate-400">
                                                        {new Date(notification.created_at).toLocaleDateString()}
                                                    </span>
                                                    <button
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            handleDismiss(notification.id);
                                                        }}
                                                        className="text-slate-300 hover:text-rose-500 opacity-0 group-hover:opacity-100 transition-all p-1"
                                                        title="مسح الإشعار"
                                                    >
                                                        <Trash2 size={14} />
                                                    </button>
                                                </div>
                                            </div>
                                            <p className="text-xs text-slate-500 mt-1 line-clamp-2">
                                                {notification.content}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                    <div className="px-4 py-2 border-t border-slate-50 text-center">
                        <button className="text-xs text-slate-400 hover:text-slate-600 transition-all font-medium">
                            عرض كل الإشعارات
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};
export default NotificationBell;

