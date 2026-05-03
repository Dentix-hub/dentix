import React, { useState } from 'react';
import { api } from '@/api';
import UsersManager from '@/features/admin/SuperAdmin/UsersManager';
import { Users } from 'lucide-react';

export default function UsersPage() {
    const [globalUsers, setGlobalUsers] = useState([]);
    const [usersLoading, setUsersLoading] = useState(false);

    // Initial fetch on mount
    React.useEffect(() => {
        handleSearchUsers('');
    }, []);

    const handleSearchUsers = async (query) => {
        setUsersLoading(true);
        try {

            const res = await api.get(`/api/v1/admin/users?search_query=${query || ''}`);
            if (Array.isArray(res.data)) {
                setGlobalUsers(res.data);
            } else if (res.data && Array.isArray(res.data.users)) {
                // Handle case where API returns { users: [...] }
                setGlobalUsers(res.data.users);
            } else {
                console.error("Unexpected API response format:", res.data);
                setGlobalUsers([]);
            }
        } catch (err) {
            console.error(err);
            alert("فشل البحث");
        } finally {
            setUsersLoading(false);
        }
    };

    const handleToggleUserStatus = async (userId, currentStatus) => {
        const action = currentStatus ? "تعطيل" : "تفعيل";
        if (!window.confirm(`هل أنت متأكد من ${action} هذا المستخدم؟`)) return;

        try {
            await api.post(`/api/v1/admin/users/${userId}/toggle-status`);
            setGlobalUsers(prev => prev.map(u =>
                u.id === userId ? { ...u, is_active: !currentStatus } : u
            ));
            alert(`تم ${action} المستخدم بنجاح`);
        } catch (err) {
            console.error(err);
            alert("فشل تغيير حالة المستخدم");
        }
    };

    return (
        <div className="space-y-6 animate-fade-in-up">
            <div className="flex items-center gap-4 bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800">
                <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-2xl text-blue-600 dark:text-blue-400">
                    <Users size={32} />
                </div>
                <div>
                    <h1 className="text-2xl font-black text-slate-800 dark:text-white">إدارة المستخدمين</h1>
                    <p className="text-slate-500 dark:text-slate-400 font-medium mt-1">البحث والتحكم في جميع مستخدمي النظام</p>
                </div>
            </div>

            <UsersManager
                users={globalUsers}
                onSearch={handleSearchUsers}
                onToggleStatus={handleToggleUserStatus}
                loading={usersLoading}
            />
        </div>
    );
}

