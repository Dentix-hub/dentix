import { useState, useEffect, useCallback } from 'react';
import logger from '@/utils/logger';
import { api } from '@/api';
import UsersManager from '@/features/admin/SuperAdmin/UsersManager';
import { Users } from 'lucide-react';
import { toast, ConfirmDialog } from '@/shared/ui';
import { useTranslation } from 'react-i18next';

export default function UsersPage() {
    const { t } = useTranslation();
    const [globalUsers, setGlobalUsers] = useState([]);
    const [usersLoading, setUsersLoading] = useState(false);

    // Confirmation dialog state
    const [confirmState, setConfirmState] = useState({
        isOpen: false,
        title: '',
        message: '',
        confirmText: '',
        variant: 'primary',
        onConfirm: () => {},
    });

    const handleSearchUsers = useCallback(async (query = '') => {
        setUsersLoading(true);
        try {
            const params = {};
            if (query && query.trim()) {
                params.search_query = query.trim();
            }
            const res = await api.get('/api/v1/admin/users', { params });
            if (Array.isArray(res.data)) {
                setGlobalUsers(res.data);
            } else if (res.data && Array.isArray(res.data.users)) {
                setGlobalUsers(res.data.users);
            } else {
                logger.error("Unexpected API response format:", res.data);
                setGlobalUsers([]);
            }
        } catch (err) {
            logger.error(err);
            toast.error(t('super_admin.users.search_fail', 'فشل البحث عن المستخدمين'));
        } finally {
            setUsersLoading(false);
        }
    }, [t]);

    // Initial fetch on mount
    useEffect(() => {
        handleSearchUsers('');
    }, [handleSearchUsers]);

    const handleToggleUserStatus = (userId, currentStatus) => {
        const actionVerb = currentStatus
            ? t('super_admin.users.deactivate_action', 'تعطيل')
            : t('super_admin.users.activate_action', 'تفعيل');

        setConfirmState({
            isOpen: true,
            title: t('super_admin.users.toggle_status_title', 'تغيير حالة المستخدم'),
            message: `${t('super_admin.users.toggle_status_msg', 'هل أنت متأكد من')} ${actionVerb} ${t('super_admin.users.this_user', 'هذا المستخدم؟')}`,
            confirmText: actionVerb,
            variant: currentStatus ? 'danger' : 'primary',
            onConfirm: async () => {
                try {
                    await api.post(`/api/v1/admin/users/${userId}/toggle-status`);
                    setGlobalUsers(prev => prev.map(u =>
                        u.id === userId ? { ...u, is_active: !currentStatus } : u
                    ));
                    toast.success(`${t('super_admin.users.status_changed_to', 'تم')} ${actionVerb} ${t('super_admin.users.user_successfully', 'المستخدم بنجاح')}`);
                } catch (err) {
                    logger.error(err);
                    toast.error(t('super_admin.users.status_change_fail', 'فشل تغيير حالة المستخدم'));
                } finally {
                    setConfirmState(prev => ({ ...prev, isOpen: false }));
                }
            }
        });
    };

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div className="flex items-center gap-4 bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800">
                <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-2xl text-blue-600 dark:text-blue-400 shrink-0">
                    <Users size={32} />
                </div>
                <div>
                    <h1 className="text-2xl font-extrabold text-slate-800 dark:text-white">
                        {t('sidebar.users', 'إدارة المستخدمين')}
                    </h1>
                    <p className="text-slate-500 dark:text-slate-400 font-medium mt-1 text-sm">
                        {t('super_admin.users.subtitle', 'البحث والتحكم في جميع مستخدمي النظام')}
                    </p>
                </div>
            </div>

            <UsersManager
                users={globalUsers}
                onSearch={handleSearchUsers}
                onToggleStatus={handleToggleUserStatus}
                loading={usersLoading}
            />

            {/* Shared Confirmation Dialog */}
            <ConfirmDialog
                isOpen={confirmState.isOpen}
                title={confirmState.title}
                message={confirmState.message}
                confirmText={confirmState.confirmText}
                variant={confirmState.variant}
                onConfirm={confirmState.onConfirm}
                onClose={() => setConfirmState(prev => ({ ...prev, isOpen: false }))}
                onCancel={() => setConfirmState(prev => ({ ...prev, isOpen: false }))}
            />
        </div>
    );
}
