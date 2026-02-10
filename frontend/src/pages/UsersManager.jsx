import { useState, useEffect } from 'react';
import { getUsers, registerUser, updateUser, deleteUser } from '../api';
import { UserPlus, Trash2, Shield, User, Edit } from 'lucide-react';
import { useTranslation } from 'react-i18next';
export default function UsersManager() {
    const { t } = useTranslation();
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [isModalOpen, setIsModalOpen] = useState(false);
    // Form
    const [newUser, setNewUser] = useState({
        username: '',
        password: '',
        role: 'doctor',
        permissions: [],
        patient_visibility_mode: 'all_assigned'
    });
    // Permission Presets
    const permissionPresets = {
        doctor: ['view_patients', 'edit_patients', 'view_treatments', 'edit_treatments', 'view_calendar'],
        assistant: ['view_patients', 'view_calendar', 'view_treatments'],
        receptionist: ['view_patients', 'view_calendar', 'edit_patients'], // edit_patients for registration
        accountant: ['view_financials', 'view_reports'],
        custom: []
    };
    // Check admin, although App.jsx protects route, this is extra safety
    useEffect(() => {
        loadUsers();
    }, []);
    const loadUsers = async () => {
        try {
            setLoading(true);
            const res = await getUsers();
            setUsers(res.data);
        } catch (err) {
            console.error(err);
            if (err.response && err.response.status === 403) {
                alert('Access Denied');
            }
        } finally {
            setLoading(false);
        }
    };
    const handleOpenModal = (user = null) => {
        if (user) {
            let perms = [];
            try {
                if (user.permissions) {
                    perms = typeof user.permissions === 'string' ? JSON.parse(user.permissions) : user.permissions;
                }
            } catch (e) {
                console.error("Error parsing permissions", e);
            }
            setNewUser({
                id: user.id,
                username: user.username,
                password: '', // Password empty on edit means unchanged
                role: user.role,
                permissions: perms,
                patient_visibility_mode: user.patient_visibility_mode || 'all_assigned'
            });
        } else {
            setNewUser({
                username: '',
                password: '',
                role: 'doctor',
                permissions: [],
                patient_visibility_mode: 'all_assigned'
            });
        }
        setIsModalOpen(true);
    };
    const handleSave = async () => {
        if (!newUser.username) return alert(t('common.messages.fill_all'));
        // Password required only for new users
        if (!newUser.id && !newUser.password) return alert(t('common.messages.fill_all'));
        try {
            const dataToSend = {
                ...newUser,
                permissions: newUser.permissions ? JSON.stringify(newUser.permissions) : ''
            };
            if (newUser.id) {
                await updateUser(newUser.id, dataToSend);
            } else {
                await registerUser(dataToSend);
            }
            setIsModalOpen(false);
            setNewUser({ username: '', password: '', role: 'doctor', permissions: [], patient_visibility_mode: 'all_assigned' });
            loadUsers();
        } catch (err) {
            alert('Failed to save user: ' + (err.response?.data?.detail || err.message));
        }
    };
    const handleDelete = async (id) => {
        if (!id) {
            console.error('Cannot delete user: id is undefined');
            return;
        }
        if (!confirm(t('users.form.delete_confirm'))) return;
        try {
            await deleteUser(id);
            loadUsers();
        } catch (err) {
            alert('Error: ' + (err.response?.data?.detail || err.message));
        }
    };
    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-2xl font-bold text-slate-800">{t('users.title')}</h2>
                    <p className="text-slate-500">{t('users.subtitle')}</p>
                </div>
                <button
                    onClick={() => handleOpenModal()}
                    className="flex items-center gap-2 px-6 py-3 bg-primary text-white font-bold rounded-xl hover:bg-sky-600 shadow-lg shadow-primary/20 transition-all"
                >
                    <UserPlus size={20} /> {t('users.add_new')}
                </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {users && users.length > 0 && users.map((user, index) => {
                    const roleConfig = {
                        admin: { bg: 'bg-purple-100 dark:bg-purple-900/30', text: 'text-purple-600', label: `🔐 ${t('users.roles.admin')}`, icon: <Shield size={24} /> },
                        doctor: { bg: 'bg-blue-100 dark:bg-blue-900/30', text: 'text-blue-600', label: `👨‍⚕️ ${t('users.roles.doctor')}`, icon: <User size={24} /> },
                        assistant: { bg: 'bg-teal-100 dark:bg-teal-900/30', text: 'text-teal-600', label: `👩‍⚕️ ${t('users.roles.assistant')}`, icon: <User size={24} /> },
                        receptionist: { bg: 'bg-amber-100 dark:bg-amber-900/30', text: 'text-amber-600', label: `📋 ${t('users.roles.receptionist')}`, icon: <User size={24} /> },
                        accountant: { bg: 'bg-emerald-100 dark:bg-emerald-900/30', text: 'text-emerald-600', label: `💰 ${t('users.roles.accountant')}`, icon: <User size={24} /> },
                        custom: { bg: 'bg-gray-100 dark:bg-gray-700', text: 'text-gray-600', label: `🛠️ ${t('users.roles.custom')}`, icon: <User size={24} /> },
                    };
                    const config = roleConfig[user.role] || roleConfig.doctor;
                    return (
                        <div key={user.id || `user-${index}`} className="bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm border border-slate-100 dark:border-white/5 flex items-center justify-between group hover:shadow-md transition-all">
                            <div className="flex items-center gap-4">
                                <div className={`p-4 rounded-full ${config.bg} ${config.text}`}>
                                    {user.role === 'admin' ? <Shield size={24} /> : <User size={24} />}
                                </div>
                                <div>
                                    <h3 className="font-bold text-lg text-slate-800 dark:text-white">{user.username}</h3>
                                    <span className={`text-xs px-2 py-1 rounded-full font-bold ${config.bg} ${config.text}`}>
                                        {config.label}
                                    </span>
                                </div>
                            </div>
                            {user.role !== 'admin' && (
                                <div className="flex gap-2">
                                    <button onClick={() => handleOpenModal(user)} className="p-2 text-slate-300 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-500/10 rounded-lg transition-colors">
                                        <Edit size={20} />
                                    </button>
                                    <button onClick={() => handleDelete(user.id)} className="p-2 text-slate-300 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 rounded-lg transition-colors">
                                        <Trash2 size={20} />
                                    </button>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
            {/* Modal */}
            {isModalOpen && (
                <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
                    <div className="bg-white w-full max-w-md rounded-2xl p-6 shadow-2xl animate-in zoom-in duration-200">
                        <h3 className="text-xl font-bold mb-4 text-slate-800">{newUser.id ? t('users.edit_user') : t('users.add_new')}</h3>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-bold text-slate-700 mb-1">{t('users.form.username')}</label>
                                <input
                                    value={newUser.username}
                                    onChange={e => setNewUser({ ...newUser, username: e.target.value })}
                                    className="w-full p-3 bg-slate-50 rounded-xl border border-slate-200 outline-none focus:border-primary transition-colors"
                                />
                            </div>
                            <div>
                                {newUser.id && <p className="text-xs text-amber-600 mb-1">{t('users.form.password_placeholder')}</p>}
                                <label className="block text-sm font-bold text-slate-700 mb-1">{t('users.form.password')}</label>
                                <input
                                    type="password"
                                    value={newUser.password}
                                    onChange={e => setNewUser({ ...newUser, password: e.target.value })}
                                    className="w-full p-3 bg-slate-50 rounded-xl border border-slate-200 outline-none focus:border-primary transition-colors"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-bold text-slate-700 mb-1">{t('users.form.role')}</label>
                                <select
                                    value={newUser.role}
                                    onChange={e => {
                                        const r = e.target.value;
                                        setNewUser({
                                            ...newUser,
                                            role: r,
                                            // Auto-fill permissions based on role, unless admin (full) or custom (empty)
                                            permissions: r === 'admin' ? [] : (permissionPresets[r] || [])
                                        });
                                    }}
                                    className="w-full p-3 bg-slate-50 rounded-xl border border-slate-200 outline-none focus:border-primary transition-colors"
                                >
                                    <option value="doctor">👨‍⚕️ {t('users.roles.doctor')}</option>
                                    <option value="assistant">👩‍⚕️ {t('users.roles.assistant')}</option>
                                    <option value="receptionist">📋 {t('users.roles.receptionist')}</option>
                                    <option value="accountant">💰 {t('users.roles.accountant')}</option>
                                    <option value="custom">🛠️ {t('users.roles.custom')}</option>
                                    <option value="admin">🔐 {t('users.roles.admin')}</option>
                                </select>
                                <p className="text-xs text-slate-400 mt-2">
                                    {newUser.role === 'custom' ? t('users.roles.custom') : ''}
                                </p>
                            </div>
                            {/* Data Visibility Mode (For Doctors) */}
                            {newUser.role === 'doctor' && (
                                <div>
                                    <label className="block text-sm font-bold text-slate-700 mb-1">{t('users.form.visibility')}</label>
                                    <select
                                        value={newUser.patient_visibility_mode}
                                        onChange={e => setNewUser({ ...newUser, patient_visibility_mode: e.target.value })}
                                        className="w-full p-3 bg-amber-50 rounded-xl border border-amber-200 outline-none focus:border-amber-500 transition-colors"
                                    >
                                        <option value="all_assigned">{t('users.form.vis_all')}</option>
                                        <option value="appointments_only">{t('users.form.vis_appt')}</option>
                                        <option value="mixed">{t('users.form.vis_mixed')}</option>
                                    </select>
                                    <p className="text-xs text-slate-400 mt-1">{t('users.form.visibility_hint')}</p>
                                </div>
                            )}
                            {/* Granular Permissions (Not for Admin) */}
                            {newUser.role !== 'admin' && (
                                <div className="border-t pt-4 mt-2">
                                    <label className="block text-sm font-bold text-slate-700 mb-2">{t('users.form.detailed_perms')}</label>
                                    <div className="grid grid-cols-2 gap-2 text-sm">
                                        {[
                                            { id: 'view_patients', label: t('users.permissions.view_patients') },
                                            { id: 'edit_patients', label: t('users.permissions.edit_patients') },
                                            { id: 'delete_patients', label: t('users.permissions.delete_patients') },
                                            { id: 'view_treatments', label: t('users.permissions.view_treatments') },
                                            { id: 'edit_treatments', label: t('users.permissions.edit_treatments') },
                                            { id: 'view_calendar', label: t('users.permissions.view_calendar') },
                                            { id: 'manage_lab', label: t('users.permissions.manage_lab') },
                                            { id: 'manage_inventory', label: t('users.permissions.manage_inventory') },
                                            { id: 'view_financials', label: t('users.permissions.view_financials') },
                                            { id: 'view_reports', label: t('users.permissions.view_reports') },
                                            { id: 'manage_users', label: t('users.permissions.manage_users') },
                                            { id: 'manage_settings', label: t('users.permissions.manage_settings') },
                                        ].map(perm => (
                                            <label key={perm.id} className="flex items-center gap-2 cursor-pointer">
                                                <input
                                                    type="checkbox"
                                                    checked={newUser.permissions?.includes(perm.id)}
                                                    onChange={e => {
                                                        const current = newUser.permissions || [];
                                                        if (e.target.checked) {
                                                            setNewUser({ ...newUser, permissions: [...current, perm.id] });
                                                        } else {
                                                            setNewUser({ ...newUser, permissions: current.filter(p => p !== perm.id) });
                                                        }
                                                    }}
                                                    className="rounded text-primary focus:ring-primary"
                                                />
                                                <span className="text-slate-600">{perm.label}</span>
                                            </label>
                                        ))}
                                    </div>
                                </div>
                            )}
                            <div className="flex justify-end gap-3 mt-6">
                                <button onClick={() => setIsModalOpen(false)} className="px-4 py-2 hover:bg-slate-100 rounded-lg font-bold text-slate-500">{t('users.form.cancel')}</button>
                                <button onClick={handleSave} className="px-6 py-2 bg-primary text-white font-bold rounded-lg hover:bg-sky-600 shadow-lg shadow-primary/20">{newUser.id ? t('users.form.update') : t('users.form.save')}</button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
