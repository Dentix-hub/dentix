/**
 * Helper generator script for P4:
 * Populates missing Arabic and English keys in translation.json with natural,
 * user-facing translations and guarantees full parity between AR and EN.
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { extractI18nKeys, flattenTranslations } from './extract-i18n-keys.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');
const arPath = path.join(rootDir, 'src', 'locales', 'ar', 'translation.json');
const enPath = path.join(rootDir, 'src', 'locales', 'en', 'translation.json');

// Explicit high-quality translations for keys that do not carry inline default text
export const EXPLICIT_TRANSLATIONS = {
    // === common ===
    'common.active': { ar: 'نشط', en: 'Active' },
    'common.expired': { ar: 'منتهي الصلاحية', en: 'Expired' },
    'common.refresh': { ar: 'تحديث', en: 'Refresh' },
    'common.enabled': { ar: 'مفعل', en: 'Enabled' },
    'common.disabled': { ar: 'معطل', en: 'Disabled' },
    'common.copy': { ar: 'نسخ', en: 'Copy' },
    'common.date_time': { ar: 'التاريخ والوقت', en: 'Date & Time' },
    'common.language': { ar: 'اللغة', en: 'Language' },
    'common.messages.fill_all': { ar: 'يرجى ملء جميع الحقول المطلوبة', en: 'Please fill in all required fields' },
    'common.currency': { ar: 'ج.م', en: 'EGP' },
    'common.error_loading_data': { ar: 'فشل تحميل البيانات. يرجى التحقق من الاتصال.', en: 'Failed to load data. Please check your connection.' },
    'common.doctor_prefix': { ar: 'د.', en: 'Dr.' },
    'common.separator': { ar: '، ', en: ', ' },

    // === sidebar ===
    'sidebar.labs': { ar: 'المعامل والتركيبات', en: 'Dental Labs' },
    'sidebar.subscription.grace_period': { ar: 'فترة سماح الاشتراك (متبقي {{count}} يوم)', en: 'Subscription grace period ({{count}} days remaining)' },
    'sidebar.subscription.expired': { ar: 'انتهت صلاحية الاشتراك', en: 'Subscription expired' },
    'sidebar.subscription.ends_today': { ar: 'ينتهي الاشتراك اليوم', en: 'Subscription ends today' },
    'sidebar.subscription.days_left': { ar: 'متبقي على الاشتراك {{count}} يوم', en: '{{count}} days left on subscription' },
    'sidebar.subscription.plan_premium': { ar: 'الخطة المميزة', en: 'Premium Plan' },
    'sidebar.subscription.plan_basic': { ar: 'الخطة الأساسية', en: 'Basic Plan' },
    'sidebar.subscription.plan_trial': { ar: 'الفترة التجريبية', en: 'Trial Period' },
    'sidebar.subscription.expired_readonly': { ar: 'انتهى الاشتراك - النظام في وضع القراءة فقط', en: 'Subscription expired — system is in read-only mode' },
    'sidebar.subscription.expiring_soon': { ar: 'ينتهي اشتراكك قريباً (متبقي {{count}} يوم)', en: 'Your subscription is expiring soon ({{count}} days remaining)' },

    // === appointments ===
    'appointments.messages.delete_error': { ar: 'فشل حذف الموعد', en: 'Failed to delete appointment' },
    'appointments.messages.voice_unsupported': { ar: 'التعرف الصوتي غير مدعوم', en: 'Voice recognition not supported' },
    'appointments.table.regular_visit': { ar: 'زيارة اعتيادية', en: 'Regular Visit' },

    // === patients ===
    'patients.archive_confirm': { ar: 'هل أنت متأكد من أرشفة هذا المريض؟', en: 'Are you sure you want to archive this patient?' },
    'patients.archive_success': { ar: 'تم أرشفة المريض بنجاح', en: 'Patient archived successfully' },
    'patients.archive_error': { ar: 'فشل أرشفة المريض', en: 'Failed to archive patient' },
    'patients.medical_conditions.none': { ar: 'لا يوجد', en: 'None' },
    'patients.medical_conditions.diabetes': { ar: 'سكري', en: 'Diabetes' },
    'patients.medical_conditions.hypertension': { ar: 'ضغط دم', en: 'Hypertension' },
    'patients.medical_conditions.heart_disease': { ar: 'أمراض القلب', en: 'Heart Disease' },
    'patients.medical_conditions.allergy': { ar: 'حساسية', en: 'Allergy' },
    'patients.medical_conditions.blood_thinners': { ar: 'سيولة دم', en: 'Blood Thinners' },
    'patients.medical_conditions.hepatitis_c': { ar: 'فيروس سي', en: 'Hepatitis C' },
    'patients.medical_conditions.thyroid': { ar: 'غدة درقية', en: 'Thyroid' },
    'patients.medical_conditions.pregnancy': { ar: 'حمل/رضاعة', en: 'Pregnancy/Lactation' },
    'patients.medical_conditions.smoking': { ar: 'تدخين', en: 'Smoking' },
    'patients.medical_conditions.other': { ar: 'أخرى', en: 'Other' },
    'patientDetails.chart.select_tooth': { ar: 'يرجى تحديد سن أولاً', en: 'Please select a tooth first' },
    'patientDetails.treatment_history.status': { ar: 'الحالة', en: 'Status' },
    'patientDetails.treatment_history.statuses.Done': { ar: 'تم الإنجاز', en: 'Done' },
    'patientDetails.treatment_history.statuses.In Progress': { ar: 'جاري التنفيذ', en: 'In Progress' },
    'patientDetails.treatment_history.statuses.Pending': { ar: 'معلق', en: 'Pending' },
    'patient_details.chart.voice_unsupported': { ar: 'التعرف الصوتي غير مدعوم في هذا المتصفح', en: 'Voice recognition not supported in this browser' },

    // === inventory ===
    'inventory.warehouses.delete_fail': { ar: 'فشل حذف المخزن', en: 'Failed to delete warehouse' },
    'inventory.warehouses.delete_error': { ar: 'حدث خطأ أثناء حذف المخزن', en: 'An error occurred while deleting warehouse' },
    'inventory.medical_conditions.none': { ar: 'لا يوجد', en: 'None' },
    'inventory.medical_conditions.diabetes': { ar: 'سكري', en: 'Diabetes' },
    'inventory.medical_conditions.hypertension': { ar: 'ضغط دم', en: 'Hypertension' },
    'inventory.medical_conditions.heart_disease': { ar: 'أزمة قلبية', en: 'Heart Disease' },
    'inventory.medical_conditions.allergy': { ar: 'حساسية', en: 'Allergy' },
    'inventory.medical_conditions.blood_thinners': { ar: 'سيولة دم', en: 'Blood Thinners' },
    'inventory.medical_conditions.hepatitis_c': { ar: 'فيروس سي', en: 'Hepatitis C' },
    'inventory.medical_conditions.thyroid': { ar: 'غدة درقية', en: 'Thyroid' },
    'inventory.medical_conditions.pregnancy': { ar: 'حمل/رضاعة', en: 'Pregnancy/Lactation' },
    'inventory.medical_conditions.smoking': { ar: 'تدخين', en: 'Smoking' },

    // === billing & insurance ===
    'billing.doctor_revenue.table.cases': { ar: 'عدد الحالات', en: 'Cases' },
    'billing.expenses.categories.general': { ar: 'عام', en: 'General' },
    'billing.expenses.categories.materials': { ar: 'خامات ومواد', en: 'Materials' },
    'billing.expenses.categories.salaries': { ar: 'رواتب وأجور', en: 'Salaries' },
    'billing.expenses.categories.rent': { ar: 'إيجار', en: 'Rent' },
    'billing.expenses.categories.utilities': { ar: 'فواتير ومرافق', en: 'Utilities' },
    'billing.expenses.categories.maintenance': { ar: 'صيانة وتجهيزات', en: 'Maintenance' },
    'billing.expenses_page.title': { ar: 'إدارة المصروفات', en: 'Expense Management' },
    'billing.expenses_page.subtitle': { ar: 'تتبع مصروفات العيادة وصافي الربح', en: 'Track clinic expenses and net profit' },
    'billing.expenses_page.notes': { ar: 'ملاحظات', en: 'Notes' },
    'billing.expenses_page.empty': { ar: 'لا توجد مصروفات مسجلة', en: 'No recorded expenses' },
    'billing.expenses_page.add_button': { ar: 'تسجيل مصروف جديد', en: 'Add New Expense' },
    'billing.expenses_page.create_fail': { ar: 'فشل في إنشاء المصروف', en: 'Failed to create expense' },
    'insurance.title': { ar: 'شركات التأمين', en: 'Insurance Companies' },
    'insurance.subtitle': { ar: 'إدارة شركات التأمين والتعاقدات', en: 'Manage insurance providers and contracts' },
    'insurance.add_btn': { ar: 'إضافة شركة تأمين', en: 'Add Company' },
    'insurance.edit_title': { ar: 'تعديل شركة التأمين', en: 'Edit Insurance Provider' },
    'insurance.add_title': { ar: 'إضافة شركة تأمين جديدة', en: 'Add New Provider' },
    'insurance.company_name': { ar: 'اسم الشركة', en: 'Company Name' },
    'insurance.code': { ar: 'كود الشركة', en: 'Company Code' },
    'insurance.email': { ar: 'البريد الإلكتروني', en: 'Email' },
    'insurance.phone': { ar: 'رقم الهاتف', en: 'Phone' },
    'insurance.address': { ar: 'العنوان', en: 'Address' },
    'insurance.save': { ar: 'حفظ', en: 'Save' },
    'insurance.cancel': { ar: 'إلغاء', en: 'Cancel' },
    'insurance.delete_confirm': { ar: 'هل أنت متأكد من رغبتك في إلغاء تفعيل هذا المزود؟', en: 'Are you sure you want to deactivate this provider?' },
    'insurance.price_lists_count': { ar: 'قوائم الأسعار المرتبطة:', en: 'Price Lists:' },

    // === backup & ai & settings & push ===
    'backup.title': { ar: 'النسخ الاحتياطي وحماية البيانات', en: 'Backup & Data Protection' },
    'backup.auto_backup_label': { ar: 'تكرار النسخ الاحتياطي التلقائي', en: 'Auto Backup Frequency' },
    'backup.off': { ar: 'إيقاف', en: 'Off' },
    'ai_chat.chat.powered_by': { ar: 'مدعوم بواسطة الذكاء الاصطناعي لـ Dentix', en: 'Powered by Smart Dent AI' },
    'ai_chat.chat.voice_enabled': { ar: 'تم تفعيل التعرف الصوتي', en: 'Voice Recognition Enabled' },
    'ai_chat.chat.voice_unsupported': { ar: 'التعرف الصوتي غير مدعوم في هذا المتصفح', en: 'Voice Recognition Not Supported' },
    'settings.push.title': { ar: 'إشعارات الويب (Push Notifications)', en: 'Web Push Notifications' },
    'settings.push.description': { ar: 'تلقي تنبيهات بالمواعيد والرسائل حتى عند إغلاق التطبيق', en: 'Receive alerts for appointments and messages even when the app is closed' },
    'settings.push.disable': { ar: 'تعطيل الإشعارات', en: 'Disable Notifications' },
    'settings.push.enable': { ar: 'تفعيل الإشعارات', en: 'Enable Notifications' },
    'settings.push.denied_hint': { ar: 'تم رفض إذن الإشعارات من إعدادات المتصفح. يرجى السماح بالإشعارات من شريط العنوان.', en: 'Notifications permission was blocked in browser settings. Please allow notifications from the address bar.' },
    'settings.push.install_hint': { ar: 'لتلقي الإشعارات على أجهزة iOS، يرجى إضافة التطبيق إلى الشاشة الرئيسية أولاً.', en: 'To receive push notifications on iOS, please add this app to your Home Screen first.' },
    'notifications.mark_read': { ar: 'تحديد كمقروء', en: 'Mark as read' },
    'dashboard.revenue': { ar: 'الإيرادات', en: 'Revenue' },
    'language.code': { ar: 'ar', en: 'en' },

    // === super_admin.impersonation ===
    'super_admin.impersonation.banner': { ar: 'وضع المحاكاة ({{scope}}): عيادة {{tenant}}{{user}}', en: 'Simulation Mode ({{scope}}): Clinic {{tenant}}{{user}}' },
    'super_admin.impersonation.read_only': { ar: 'قراءة فقط', en: 'Read-only' },
    'super_admin.impersonation.full_access': { ar: 'وصول كامل', en: 'Full Access' },
    'super_admin.impersonation.tenant_fallback': { ar: 'المستأجر', en: 'Tenant' },
    'super_admin.impersonation.return': { ar: 'العودة للوحة الإشراف', en: 'Return to Admin Panel' },

    // === super_admin.ai ===
    'super_admin.ai.logs.no_logs': { ar: 'لا توجد سجلات ذكاء اصطناعي مسجلة', en: 'No AI logs recorded' },

    // === super_admin.tenants ===
    'super_admin.tenants.clinic_name': { ar: 'اسم العيادة', en: 'Clinic Name' },

    // === super_admin.plans ===
    'super_admin.plans.current_plan': { ar: 'الخطة الحالية', en: 'Current Plan' },
    'super_admin.plans.remaining_duration': { ar: 'المدة المتبقية', en: 'Remaining Duration' },
    'super_admin.plans.expiry': { ar: 'تاريخ الانتهاء', en: 'Expiry Date' },
    'super_admin.plans.trial': { ar: 'تجريبي', en: 'Trial' },
    'super_admin.plans.save_success': { ar: 'تم حفظ الخطة بنجاح', en: 'Plan saved successfully' },
    'super_admin.plans.error_saving': { ar: 'فشل حفظ الخطة', en: 'Failed to save plan' },
    'super_admin.plans.error_missing_code': { ar: 'يرجى كتابة كود الخطة', en: 'Plan code is required' },
    'super_admin.plans.error_invalid_price': { ar: 'السعر غير صحيح', en: 'Invalid price amount' },
    'super_admin.plans.error_invalid_duration': { ar: 'المدة بالأيام غير صحيحة', en: 'Invalid duration in days' },
    'super_admin.plans.custom_features_placeholder': { ar: 'ميزات مخصصة (ميزة في كل سطر)', en: 'Custom features (one per line)' },
    'super_admin.plans.delete_plan': { ar: 'حذف الخطة', en: 'Delete Plan' },
    'super_admin.plans.delete_title': { ar: 'تأكيد حذف الخطة', en: 'Confirm Plan Deletion' },

    // === super_admin.audit ===
    'super_admin.audit.system_global': { ar: 'سجل عام للنظام', en: 'Global System Audit' },
    'super_admin.audit.export_success': { ar: 'تم تصدير سجل التدقيق بنجاح', en: 'Audit log exported successfully' },
    'super_admin.audit.view_details': { ar: 'عرض التفاصيل', en: 'View Details' },

    // === super_admin.features ===
    'super_admin.features.rollout_invalid': { ar: 'نسبة الإطلاق يجب أن تكون بين 0 و 100', en: 'Rollout percentage must be between 0 and 100' },
    'super_admin.features.global_update_fail': { ar: 'فشل تحديث حالة الميزة العامة', en: 'Failed to update global feature state' },
    'super_admin.features.rollout_label': { ar: 'نسبة الإطلاق التدريجي', en: 'Rollout Percentage' },
    'super_admin.features.enable': { ar: 'تفعيل', en: 'Enable' },
    'super_admin.features.disable': { ar: 'تعطيل', en: 'Disable' },
    'super_admin.features.close_create': { ar: 'إلغاء الإضافة', en: 'Cancel Creation' },
    'super_admin.features.feature_key_label': { ar: 'مفتاح الميزة (Feature Key)', en: 'Feature Key' },
    'super_admin.features.rollout_percentage_label': { ar: 'نسبة النشر (%)', en: 'Rollout Percentage (%)' },

    // === super_admin.notifications ===
    'super_admin.notifications.date_col': { ar: 'التاريخ', en: 'Date' },
    'super_admin.notifications.delete_notif': { ar: 'حذف الإشعار', en: 'Delete Notification' },
    'super_admin.notifications.delete_title': { ar: 'تأكيد حذف الإشعار', en: 'Confirm Notification Deletion' },
    'super_admin.notifications.delete_confirm_msg': { ar: 'هل أنت متأكد من رغبتك في حذف هذا الإشعار بشكل نهائي؟', en: 'Are you sure you want to permanently delete this notification?' },
    'super_admin.notifications.error_fill_required': { ar: 'يرجى ملء الحقول المطلوبة', en: 'Please fill in required fields' },
    'super_admin.notifications.error_select_tenant': { ar: 'يرجى اختيار العيادة المستهدفة', en: 'Please select a target clinic' },
    'super_admin.notifications.success_sent': { ar: 'تم إرسال الإشعار بنجاح', en: 'Notification sent successfully' },
    'super_admin.notifications.error_sending': { ar: 'فشل إرسال الإشعار', en: 'Failed to send notification' },
    'super_admin.notifications.success_deleted': { ar: 'تم حذف الإشعار بنجاح', en: 'Notification deleted successfully' },
    'super_admin.notifications.error_deleting': { ar: 'فشل حذف الإشعار', en: 'Failed to delete notification' },

    // === super_admin.security ===
    'super_admin.security.unblock_success': { ar: 'تم إلغاء الحظر بنجاح', en: 'Successfully unblocked' },
    'super_admin.security.level_critical': { ar: 'حرج', en: 'Critical' },
    'super_admin.security.level_moderate': { ar: 'متوسط', en: 'Moderate' },
    'super_admin.security.level_optimal': { ar: 'آمن ومثالي', en: 'Optimal' },
    'super_admin.security.no_recent_failures': { ar: 'لا توجد محاولات دخول فاشلة حديثاً', en: 'No recent login failures' },
    'super_admin.security.unblock_confirm_title': { ar: 'تأكيد إلغاء الحظر', en: 'Confirm Unblock' },
    'super_admin.security.unblock_confirm_msg': { ar: 'هل أنت متأكد من رغبتك في رفع الحظر عن هذا العنوان/المستخدم؟', en: 'Are you sure you want to unblock this address/user?' },

    // === super_admin.sessions ===
    'super_admin.sessions.fetch_error': { ar: 'فشل جلب الجلسات النشطة', en: 'Failed to fetch active sessions' },
    'super_admin.sessions.terminate_success': { ar: 'تم إنهاء الجلسة بنجاح', en: 'Session terminated successfully' },
    'super_admin.sessions.terminate_failed': { ar: 'فشل إنهاء الجلسة', en: 'Failed to terminate session' },
    'super_admin.sessions.loading': { ar: 'جاري تحميل الجلسات...', en: 'Loading sessions...' },
    'super_admin.sessions.title': { ar: 'إدارة الجلسات النشطة', en: 'Active Sessions Management' },
    'super_admin.sessions.subtitle': { ar: 'مراقبة الجلسات المفتوحة للمستخدمين مع إمكانية الإنهاء الفوري', en: 'Monitor active user sessions with instant termination capability' },
    'super_admin.sessions.search_placeholder': { ar: 'بحث في الجلسات...', en: 'Search sessions...' },
    'super_admin.sessions.anonymous_user': { ar: 'مستخدم غير معرف', en: 'Anonymous User' },
    'super_admin.sessions.terminate_btn': { ar: 'إنهاء الجلسة', en: 'Terminate Session' },
    'super_admin.sessions.last_active': { ar: 'آخر نشاط', en: 'Last Active' },
    'super_admin.sessions.start_time': { ar: 'بداية الجلسة', en: 'Session Start' },
    'super_admin.sessions.no_search_matches': { ar: 'لا توجد جلسات تطابق البحث', en: 'No sessions matching search' },
    'super_admin.sessions.no_active_sessions': { ar: 'لا توجد جلسات نشطة حالياً', en: 'No active sessions currently' },
    'super_admin.sessions.terminate_confirm_title': { ar: 'تأكيد إنهاء الجلسة', en: 'Confirm Session Termination' },
    'super_admin.sessions.terminate_confirm_msg': { ar: 'هل أنت متأكد من إنهاء هذه الجلسة؟ سيتم تسجيل خروج المستخدم فوراً.', en: 'Are you sure you want to terminate this session? The user will be logged out immediately.' },
    'super_admin.sessions.terminate_confirm_btn': { ar: 'إنهاء الجلسة', en: 'Terminate Session' },

    // === super_admin.settings ===
    'super_admin.settings.save_success': { ar: 'تم حفظ الإعدادات بنجاح', en: 'Settings saved successfully' },
    'super_admin.settings.save_fail': { ar: 'فشل حفظ الإعدادات', en: 'Failed to save settings' },
    'super_admin.settings.maintenance_title': { ar: 'وضع الصيانة العام', en: 'Global Maintenance Mode' },
    'super_admin.settings.maintenance_desc': { ar: 'عند تفعيل وضع الصيانة، يتم منع المستخدمين من الوصول إلى النظام مؤقتاً باستثناء المشرفين.', en: 'When maintenance mode is active, non-admin users will be temporarily blocked from accessing the system.' },
    'super_admin.settings.maintenance_toggle': { ar: 'تفعيل وضع الصيانة', en: 'Enable Maintenance Mode' },
    'super_admin.settings.announcement_title': { ar: 'إعلان شريط النظام', en: 'System Banner Announcement' },
    'super_admin.settings.announcement_desc': { ar: 'إظهار شريط إعلاني أعلى الشاشة لجميع المستخدمين في النظام', en: 'Display a banner announcement at the top of the screen for all users' },
    'super_admin.settings.announcement_placeholder': { ar: 'اكتب نص الإعلان هنا...', en: 'Type announcement text here...' },
    'super_admin.settings.save_changes': { ar: 'حفظ التغييرات', en: 'Save Changes' },
    'super_admin.settings.support_info_title': { ar: 'بيانات التواصل والدعم الفني', en: 'Technical Support Info' },
    'super_admin.settings.support_info_desc': { ar: 'معلومات الدعم الفني المعروضة للعيادات داخل النظام', en: 'Support contact information shown to clinics within the system' },
    'super_admin.settings.support_phone': { ar: 'هاتف الدعم', en: 'Support Phone' },
    'super_admin.settings.support_whatsapp': { ar: 'واتساب الدعم', en: 'Support WhatsApp' },
    'super_admin.settings.support_email': { ar: 'بريد الدعم', en: 'Support Email' },
    'super_admin.settings.support_working_hours': { ar: 'ساعات العمل', en: 'Working Hours' },
    'super_admin.settings.maintenance_confirm_title': { ar: 'تأكيد تغيير وضع الصيانة', en: 'Confirm Maintenance Mode Change' },
    'super_admin.settings.maintenance_disable_confirm': { ar: 'هل أنت متأكد من رغبتك في إلغاء وضع الصيانة وإعادة إتاحة النظام للجميع؟', en: 'Are you sure you want to disable maintenance mode and reopen the system for everyone?' },
    'super_admin.settings.maintenance_enable_confirm': { ar: 'هل أنت متأكد من تفعيل وضع الصيانة؟ سيتم حظر المستخدمين غير المشرفين.', en: 'Are you sure you want to enable maintenance mode? Non-admin users will be blocked.' },

    // === super_admin.support ===
    'super_admin.support.error_updating_status': { ar: 'فشل تحديث حالة الرسالة', en: 'Failed to update message status' },
    'super_admin.support.message_body': { ar: 'نص الرسالة', en: 'Message Body' },
    'super_admin.support.delete_title': { ar: 'تأكيد حذف الرسالة', en: 'Confirm Message Deletion' },
    'super_admin.support.delete_confirm_msg': { ar: 'هل أنت متأكد من حذف هذه الرسالة من الدعم الفني؟', en: 'Are you sure you want to delete this support message?' },
    'super_admin.support.success_deleted': { ar: 'تم حذف الرسالة بنجاح', en: 'Message deleted successfully' },
    'super_admin.support.error_deleting': { ar: 'فشل حذف الرسالة', en: 'Failed to delete message' },

    // === super_admin.health ===
    'super_admin.health.status_success': { ar: 'ناجح', en: 'Success' },
    'super_admin.health.status_running': { ar: 'قيد التشغيل', en: 'Running' },
    'super_admin.health.status_pending': { ar: 'قيد الانتظار', en: 'Pending' },
    'super_admin.health.status_failed': { ar: 'فاشل', en: 'Failed' },
    'super_admin.health.overall_status': { ar: 'حالة النظام الإجمالية', en: 'Overall System Health' },
    'super_admin.health.overview_desc': { ar: 'متابعة أداء الخدمات والمهام الخلفية وقواعد البيانات', en: 'Monitor services performance, background workers, and database health' },
    'super_admin.health.no_active_alerts': { ar: 'لا توجد تنبيهات نشطة حالياً', en: 'No active alerts currently' },
    'super_admin.health.job_success_rate': { ar: 'معدل نجاح المهام', en: 'Job Success Rate' },
    'super_admin.health.recent_jobs': { ar: 'المهام الخلفية الحديثة', en: 'Recent Background Jobs' },
    'super_admin.health.job_status': { ar: 'حالة المهمة', en: 'Job Status' },
    'super_admin.health.job_duration': { ar: 'المدة', en: 'Duration' },
    'super_admin.health.job_triggered_by': { ar: 'مُشغّل المهمة', en: 'Triggered By' },
    'super_admin.health.job_started_at': { ar: 'وقت البدء', en: 'Started At' },
    'super_admin.health.loading_jobs': { ar: 'جاري تحميل المهام...', en: 'Loading jobs...' },
    'super_admin.health.no_jobs': { ar: 'لا توجد مهام مسجلة', en: 'No recorded jobs' },
    'super_admin.health.unnamed_job': { ar: 'مهمة بدون اسم', en: 'Unnamed Job' },

    // === super_admin.tenant_detail ===
    'super_admin.tenant_detail.unavailable': { ar: 'غير متوفر', en: 'Unavailable' },
    'super_admin.tenant_detail.title': { ar: 'تفاصيل العيادة', en: 'Clinic Details' },
    'super_admin.tenant_detail.close_drawer': { ar: 'إغلاق اللوحة', en: 'Close Drawer' },
    'super_admin.tenant_detail.subtitle': { ar: 'إدارة بيانات وموارد المستأجر', en: 'Manage tenant data and resources' },
    'super_admin.tenant_detail.load_failed': { ar: 'فشل تحميل بيانات العيادة', en: 'Failed to load clinic details' },
    'super_admin.tenant_detail.retry_hint': { ar: 'يرجى إعادة المحاولة لاحقاً', en: 'Please try again later' },
    'super_admin.tenant_detail.unnamed': { ar: 'بدون اسم', en: 'Unnamed' },
    'super_admin.tenant_detail.clinic_number': { ar: 'رقم العيادة:', en: 'Clinic #:' },
    'super_admin.tenant_detail.auto_admin': { ar: 'مدير تلقائي', en: 'Auto Admin' },
    'super_admin.tenant_detail.reason_placeholder': { ar: 'سبب الدخول (5 أحرف على الأقل)', en: 'Access reason (at least 5 characters)' },
    'super_admin.tenant_detail.readonly_scope': { ar: 'نطاق الجلسة: قراءة فقط (Read-Only)', en: 'Session Scope: Read-Only' },
    'super_admin.tenant_detail.min_reason': { ar: 'الحد الأدنى 5 أحرف', en: 'Minimum 5 characters' },
    'super_admin.tenant_detail.start_impersonation': { ar: 'دخول مؤقت للنظام', en: 'Start Impersonation' },
    'super_admin.tenant_detail.patients': { ar: 'المرضى', en: 'Patients' },
    'super_admin.tenant_detail.appointments': { ar: 'المواعيد', en: 'Appointments' },
    'super_admin.tenant_detail.revenue': { ar: 'الإيرادات', en: 'Revenue' },
    'super_admin.tenant_detail.current_plan': { ar: 'الخطة الحالية', en: 'Current Plan' },
    'super_admin.tenant_detail.contact_info': { ar: 'بيانات الاتصال', en: 'Contact Info' },
    'super_admin.tenant_detail.email': { ar: 'البريد الإلكتروني', en: 'Email' },
    'super_admin.tenant_detail.phone': { ar: 'الهاتف', en: 'Phone' },
    'super_admin.tenant_detail.activity_title': { ar: 'النشاط والتسجيل', en: 'Activity & Registration' },
    'super_admin.tenant_detail.joined': { ar: 'تاريخ الانضمام', en: 'Joined Date' },
    'super_admin.tenant_detail.last_activity': { ar: 'آخر نشاط', en: 'Last Activity' },
    'super_admin.tenant_detail.no_activity': { ar: 'لا يوجد نشاط مسجل', en: 'No activity recorded' },

    // === super_admin.two_factor ===
    'super_admin.two_factor.invalid_setup_payload': { ar: 'بيانات إعداد المصادقة الثنائية غير صحيحة', en: 'Invalid two-factor setup data' },
    'super_admin.two_factor.setup_fail': { ar: 'فشل إعداد المصادقة الثنائية', en: 'Failed to setup two-factor authentication' },
    'super_admin.two_factor.missing_secret': { ar: 'المفتاح السري مفقود', en: 'Secret key is missing' },
    'super_admin.two_factor.code_length_error': { ar: 'رمز التحقق يجب أن يتكون من 6 أرقام', en: 'Verification code must be 6 digits' },
    'super_admin.two_factor.enable_success': { ar: 'تم تفعيل المصادقة الثنائية بنجاح', en: 'Two-factor authentication enabled successfully' },
    'super_admin.two_factor.invalid_code': { ar: 'رمز التحقق غير صحيح، يرجى المحاولة ثانية', en: 'Invalid code, please try again' },
    'super_admin.two_factor.disable_success': { ar: 'تم تعطيل المصادقة الثنائية بنجاح', en: 'Two-factor authentication disabled successfully' },
    'super_admin.two_factor.disable_fail': { ar: 'فشل تعطيل المصادقة الثنائية', en: 'Failed to disable two-factor authentication' },
    'super_admin.two_factor.secret_copied': { ar: 'تم نسخ المفتاح السري', en: 'Secret key copied to clipboard' },
    'super_admin.two_factor.clipboard_unsupported': { ar: 'الحافظة غير مدعومة في هذا المتصفح', en: 'Clipboard not supported in this browser' },
    'super_admin.two_factor.clipboard_fail': { ar: 'فشل نسخ المفتاح إلى الحافظة', en: 'Failed to copy to clipboard' },
    'super_admin.two_factor.title': { ar: 'المصادقة الثنائية (2FA)', en: 'Two-Factor Authentication (2FA)' },
    'super_admin.two_factor.subtitle': { ar: 'تأمين حسابك برمز تحقق إضافي من تطبيق المصادقة', en: 'Secure your account with an extra verification code from an authenticator app' },
    'super_admin.two_factor.desc': { ar: 'أضف طبقة حماية إضافية لحسابك لمنع الوصول غير المصرح به.', en: 'Add an extra layer of protection to your account to prevent unauthorized access.' },
    'super_admin.two_factor.start_setup': { ar: 'بدء الإعداد', en: 'Start Setup' },
    'super_admin.two_factor.scan_qr': { ar: 'امسح رمز QR', en: 'Scan QR Code' },
    'super_admin.two_factor.scan_qr_desc': { ar: 'امسح الرمز باستخدام تطبيق مثل Google Authenticator أو Authy', en: 'Scan the code using an app like Google Authenticator or Authy' },
    'super_admin.two_factor.manual_secret': { ar: 'أو أدخل المفتاح السري يدوياً:', en: 'Or enter the secret key manually:' },
    'super_admin.two_factor.enter_code': { ar: 'أدخل رمز التحقق (6 أرقام)', en: 'Enter 6-digit code' },
    'super_admin.two_factor.activate_now': { ar: 'تفعيل الآن', en: 'Activate Now' },
    'super_admin.two_factor.enabled_desc': { ar: 'المصادقة الثنائية مفعلة حالياً على حسابك وتوفر أعلى درجات الأمان.', en: 'Two-factor authentication is currently enabled on your account providing maximum security.' },
    'super_admin.two_factor.disable_btn': { ar: 'تعطيل المصادقة الثنائية', en: 'Disable Two-Factor' },
    'super_admin.two_factor.disable_confirm_title': { ar: 'تأكيد تعطيل المصادقة الثنائية', en: 'Confirm Disabling Two-Factor' },
    'super_admin.two_factor.disable_confirm_msg': { ar: 'هل أنت متأكد من رغبتك في تعطيل المصادقة الثنائية؟ سيؤدي ذلك لخفض أمان حسابك.', en: 'Are you sure you want to disable two-factor authentication? This reduces account security.' },

    // === super_admin.communications ===
    'super_admin.communications.loading': { ar: 'جاري تحميل المراسلات...', en: 'Loading communications...' },
    'super_admin.communications.title': { ar: 'مركز التواصل والإشعارات', en: 'Communications & Notifications Center' },
    'super_admin.communications.subtitle': { ar: 'إرسال التنبيهات ومتابعة رسائل الدعم الفني', en: 'Send announcements and manage support inquiries' },
    'super_admin.communications.tabs.messages': { ar: 'رسائل الدعم', en: 'Support Messages' },
    'super_admin.communications.tabs.notifications': { ar: 'الإشعارات العامة', en: 'Global Notifications' },

    // === super_admin.payments ===
    'super_admin.payments.error_select_tenant': { ar: 'يرجى اختيار العيادة أولاً', en: 'Please select a clinic first' },
    'super_admin.payments.error_select_plan': { ar: 'يرجى اختيار الخطة', en: 'Please select a plan' },
    'super_admin.payments.error_invalid_amount': { ar: 'مبلغ الدفعة غير صحيح', en: 'Invalid payment amount' },
    'super_admin.payments.error_invalid_date': { ar: 'تاريخ الدفعة غير صحيح', en: 'Invalid payment date' },
    'super_admin.payments.success_recorded': { ar: 'تم تسجيل الدفعة بنجاح', en: 'Payment recorded successfully' },
    'super_admin.payments.error_recording': { ar: 'فشل تسجيل الدفعة', en: 'Failed to record payment' },
    'super_admin.payments.success_deleted': { ar: 'تم حذف الدفعة بنجاح', en: 'Payment deleted successfully' },
    'super_admin.payments.error_deleting': { ar: 'فشل حذف الدفعة', en: 'Failed to delete payment' },
    'super_admin.payments.modal_title': { ar: 'تسجيل دفعة اشتراك جديدة', en: 'Record Subscription Payment' },
    'super_admin.payments.modal_subtitle': { ar: 'إدخال تفاصيل الدفعة المالية وتحديث حالة الاشتراك', en: 'Enter payment details and update subscription status' },
    'super_admin.payments.select_clinic': { ar: 'اختر العيادة', en: 'Select Clinic' },
    'super_admin.payments.select_user': { ar: 'المستخدم / الطبيب المسؤول', en: 'Responsible Doctor / User' },
    'super_admin.payments.notes_placeholder': { ar: 'ملاحظات إضافية حول الدفعة...', en: 'Additional notes regarding payment...' },
    'super_admin.payments.submit_button': { ar: 'تأكيد وحفظ الدفعة', en: 'Confirm & Save Payment' },
    'super_admin.payments.delete_confirm_msg': { ar: 'هل أنت متأكد من حذف هذه الدفعة من السجلات المالية؟', en: 'Are you sure you want to delete this payment record?' },

    // === super_admin.logs ===
    'super_admin.logs.delete_success': { ar: 'تم حذف السجل بنجاح', en: 'Log deleted successfully' },
    'super_admin.logs.delete_failed': { ar: 'فشل حذف السجل', en: 'Failed to delete log' },
    'super_admin.logs.clear_success': { ar: 'تم مسح السجلات بنجاح', en: 'Logs cleared successfully' },
    'super_admin.logs.clear_failed': { ar: 'فشل مسح السجلات', en: 'Failed to clear logs' },
    'super_admin.logs.export_success': { ar: 'تم تصدير السجلات بنجاح', en: 'Logs exported successfully' },
    'super_admin.logs.export_failed': { ar: 'فشل تصدير السجلات', en: 'Failed to export logs' },
    'super_admin.logs.copy_success': { ar: 'تم نسخ تفاصيل السجل', en: 'Log details copied to clipboard' },
    'super_admin.logs.copy_failed': { ar: 'فشل نسخ السجل', en: 'Failed to copy log' },
    'super_admin.logs.col_level': { ar: 'المستوى', en: 'Level' },
    'super_admin.logs.col_source': { ar: 'المصدر', en: 'Source' },
    'super_admin.logs.col_message': { ar: 'الرسالة', en: 'Message' },
    'super_admin.logs.col_path': { ar: 'المسار', en: 'Path' },
    'super_admin.logs.col_date': { ar: 'التاريخ', en: 'Date' },
    'super_admin.logs.col_actions': { ar: 'الإجراءات', en: 'Actions' },
    'super_admin.logs.action_view': { ar: 'عرض', en: 'View' },
    'super_admin.logs.action_copy': { ar: 'نسخ', en: 'Copy' },
    'super_admin.logs.action_delete': { ar: 'حذف', en: 'Delete' },
    'super_admin.logs.title': { ar: 'سجلات أحداث النظام', en: 'System Logs' },
    'super_admin.logs.subtitle': { ar: 'متابعة سجلات الخادم والأخطاء والتحذيرات اللحظية', en: 'Monitor server logs, errors, and real-time warnings' },
    'super_admin.logs.export_csv': { ar: 'تصدير CSV', en: 'Export CSV' },
    'super_admin.logs.clear_all': { ar: 'مسح الكل', en: 'Clear All' },
    'super_admin.logs.fetch_error': { ar: 'فشل جلب سجلات النظام', en: 'Failed to fetch system logs' },
    'super_admin.logs.empty_msg': { ar: 'لا توجد سجلات تطابق الفلترة الحالية', en: 'No logs matching current filter' },
    'super_admin.logs.detail_title': { ar: 'تفاصيل سجل الحدث', en: 'Log Event Details' },
    'super_admin.logs.copy_details': { ar: 'نسخ التفاصيل', en: 'Copy Details' },
    'super_admin.logs.delete_title': { ar: 'تأكيد حذف السجل', en: 'Confirm Log Deletion' },
    'super_admin.logs.delete_confirm_msg': { ar: 'هل أنت متأكد من حذف هذا السجل بشكل نهائي؟', en: 'Are you sure you want to permanently delete this log?' },
    'super_admin.logs.clear_title': { ar: 'تأكيد مسح كافة السجلات', en: 'Confirm Clear All Logs' },
    'super_admin.logs.clear_confirm_msg': { ar: 'هل أنت متأكد من مسح جميع السجلات؟ لا يمكن التراجع عن هذا الإجراء.', en: 'Are you sure you want to clear all logs? This action cannot be undone.' },

    // === super_admin.system & backup ===
    'super_admin.backup.oauth_success': { ar: 'تم ربط Google Drive بنجاح', en: 'Google Drive connected successfully' },
    'super_admin.backup.oauth_failed': { ar: 'فشل ربط Google Drive', en: 'Failed to connect Google Drive' },
    'super_admin.backup.oauth_error': { ar: 'حدث خطأ أثناء الاتصال بمصادقة Google', en: 'An error occurred during Google OAuth' },
    'super_admin.profile.no_changes_error': { ar: 'لم يتم إجراء أي تعديلات للحفظ', en: 'No changes to save' },
    'super_admin.profile.update_success': { ar: 'تم تحديث البيانات بنجاح', en: 'Profile updated successfully' },
    'super_admin.profile.update_fail': { ar: 'فشل تحديث البيانات', en: 'Failed to update profile' },
    'super_admin.backup.drive_not_configured': { ar: 'لم يتم إعداد مسار النسخ السحابي بعد', en: 'Cloud backup target not configured yet' },
    'super_admin.backup.connect_failed': { ar: 'فشل الاتصال بخدمة التخزين السحابي', en: 'Failed to connect to cloud storage service' },
    'super_admin.backup.started_msg': { ar: 'تم بدء عملية النسخ الاحتياطي في الخلفية', en: 'Backup process started in background' },
    'super_admin.backup.trigger_failed': { ar: 'فشل بدء عملية النسخ الاحتياطي', en: 'Failed to trigger backup process' },
    'super_admin.backup.disconnect_success': { ar: 'تم فصل خدمة Google Drive بنجاح', en: 'Google Drive disconnected successfully' },
    'super_admin.backup.disconnect_fail': { ar: 'فشل فصل Google Drive', en: 'Failed to disconnect Google Drive' },
    'super_admin.system.loading': { ar: 'جاري تحميل إعدادات النظام...', en: 'Loading system settings...' },
    'super_admin.system.tabs.settings': { ar: 'الإعدادات العامة', en: 'General Settings' },
    'super_admin.system.tabs.features': { ar: 'الميزات التجريبية', en: 'Feature Flags' },
    'super_admin.system.tabs.profile': { ar: 'الملف الشخصي', en: 'Profile' },
    'super_admin.system.tabs.backup': { ar: 'النسخ السحابي', en: 'Cloud Backup' },
    'super_admin.system.tabs.security': { ar: 'الأمان والحماية', en: 'Security' },
    'super_admin.system.tabs.sessions': { ar: 'الجلسات المفتوحة', en: 'Active Sessions' },
    'super_admin.system.title': { ar: 'إدارة وإعدادات النظام', en: 'System Settings & Administration' },
    'super_admin.system.subtitle': { ar: 'التحكم المركزي في خيارات المنصة والصيانة والنسخ الاحتياطي والأمان', en: 'Central control over platform options, maintenance, backups, and security' },
    'super_admin.profile.title': { ar: 'تعديل الملف الشخصي للمشرف', en: 'Edit Admin Profile' },
    'super_admin.profile.username_label': { ar: 'اسم المستخدم', en: 'Username' },
    'super_admin.profile.unchanged_placeholder': { ar: 'اتركه فارغاً دون تغيير', en: 'Leave blank to keep unchanged' },
    'super_admin.profile.email_label': { ar: 'البريد الإلكتروني', en: 'Email' },
    'super_admin.profile.password_label': { ar: 'كلمة المرور الجديدة', en: 'New Password' },
    'super_admin.profile.save_changes': { ar: 'تحديث الحساب', en: 'Update Account' },
    'super_admin.backup.policy_title': { ar: 'سياسة النسخ الاحتياطي المركزي', en: 'Central Backup Policy' },
    'super_admin.backup.policy_desc': { ar: 'تحديد دورية النسخ وتخزين النسخ المشفرة على السحابة', en: 'Configure backup frequency and encrypted cloud storage' },
    'super_admin.backup.drive_title': { ar: 'النسخ السحابي عبر Google Drive', en: 'Google Drive Cloud Backup' },
    'super_admin.backup.drive_subtitle': { ar: 'ربط حساب Google Drive لتخزين النسخ الدورية تلقائياً', en: 'Connect Google Drive to store scheduled backups automatically' },
    'super_admin.backup.connected': { ar: 'متصل', en: 'Connected' },
    'super_admin.backup.disconnected': { ar: 'غير متصل', en: 'Disconnected' },
    'super_admin.backup.last_run_label': { ar: 'آخر نسخة احتياطية:', en: 'Last Backup:' },
    'super_admin.backup.no_runs_yet': { ar: 'لم يتم التشغيل بعد', en: 'Not run yet' },
    'super_admin.backup.status_success': { ar: 'مكتمل بنجاح', en: 'Completed successfully' },
    'super_admin.backup.status_processing': { ar: 'جاري النسخ...', en: 'Processing...' },
    'super_admin.backup.status_failed': { ar: 'فشل النسخ', en: 'Failed' },
    'super_admin.backup.connect_btn': { ar: 'ربط Google Drive', en: 'Connect Google Drive' },
    'super_admin.backup.starting': { ar: 'جاري البدء...', en: 'Starting...' },
    'super_admin.backup.trigger_cloud_btn': { ar: 'بدء نسخة سحابية الآن', en: 'Trigger Cloud Backup Now' },
    'super_admin.backup.disconnecting': { ar: 'جاري الفصل...', en: 'Disconnecting...' },
    'super_admin.backup.disconnect_btn': { ar: 'فصل Google Drive', en: 'Disconnect Google Drive' },
    'super_admin.profile.confirm_title': { ar: 'تأكيد تحديث بيانات المشرف', en: 'Confirm Profile Update' },
    'super_admin.profile.confirm_msg': { ar: 'هل أنت متأكد من رغبتك في حفظ بيانات المشرف الجديدة؟', en: 'Are you sure you want to save the new admin credentials?' },
    'super_admin.backup.confirm_upload_title': { ar: 'تأكيد بدء النسخ السحابي', en: 'Confirm Cloud Backup Start' },
    'super_admin.backup.confirm_upload_msg': { ar: 'سيتم أخذ لقطة كاملة لقاعدة البيانات ورفعها إلى السحابة فوراً. هل ترغب في المتابعة؟', en: 'A full snapshot of the database will be taken and uploaded immediately. Continue?' },
    'super_admin.backup.confirm_start_btn': { ar: 'بدء النسخ', en: 'Start Backup' },
    'super_admin.backup.disconnect_confirm_title': { ar: 'تأكيد فصل Google Drive', en: 'Confirm Google Drive Disconnect' },
    'super_admin.backup.disconnect_confirm_msg': { ar: 'هل أنت متأكد من فصل الحساب السحابي؟ ستتوقف النسخ الاحتياطية التلقائية إلى Google Drive.', en: 'Are you sure you want to disconnect? Automated backups to Google Drive will be paused.' },
};

function setDeep(target, pathParts, value) {
    let curr = target;
    for (let i = 0; i < pathParts.length - 1; i++) {
        const part = pathParts[i];
        if (!curr[part] || typeof curr[part] !== 'object' || Array.isArray(curr[part])) {
            curr[part] = {};
        }
        curr = curr[part];
    }
    const last = pathParts[pathParts.length - 1];
    curr[last] = value;
}

export function buildAndApplyTranslations() {
    const report = extractI18nKeys();
    const arJson = JSON.parse(fs.readFileSync(arPath, 'utf8'));
    const enJson = JSON.parse(fs.readFileSync(enPath, 'utf8'));

    const arFlat = flattenTranslations(arJson);
    const enFlat = flattenTranslations(enJson);

    let addedToAr = 0;
    let addedToEn = 0;

    // 1. Apply explicit translations first
    for (const [key, trans] of Object.entries(EXPLICIT_TRANSLATIONS)) {
        if (!(key in arFlat)) {
            setDeep(arJson, key.split('.'), trans.ar);
            arFlat[key] = trans.ar;
            addedToAr++;
        }
        if (!(key in enFlat)) {
            setDeep(enJson, key.split('.'), trans.en);
            enFlat[key] = trans.en;
            addedToEn++;
        }
    }

    // 2. For all static keys found in code:
    for (const item of report.staticKeys) {
        const key = item.key;
        const defaultText = item.defaultText;

        const hasAr = key in arFlat;
        const hasEn = key in enFlat;

        if (hasAr && hasEn) continue;

        let arVal = hasAr ? arFlat[key] : null;
        let enVal = hasEn ? enFlat[key] : null;

        if (!arVal && !enVal && defaultText) {
            // Check if defaultText contains Arabic
            const isArabic = /[\u0600-\u06FF]/.test(defaultText);
            if (isArabic) {
                arVal = defaultText;
                // Generate simple English fallback from key or translation
                enVal = generateEnglishFromKeyOrDefault(key, defaultText);
            } else {
                enVal = defaultText;
                arVal = generateArabicFromKeyOrDefault(key, defaultText);
            }
        } else if (!arVal && enVal) {
            arVal = generateArabicFromKeyOrDefault(key, enVal);
        } else if (!enVal && arVal) {
            enVal = generateEnglishFromKeyOrDefault(key, arVal);
        } else if (!arVal && !enVal) {
            // Fallback for any remaining key
            enVal = titleCaseFromKey(key);
            arVal = generateArabicFromKeyOrDefault(key, enVal);
        }

        if (!hasAr && arVal) {
            setDeep(arJson, key.split('.'), arVal);
            arFlat[key] = arVal;
            addedToAr++;
        }
        if (!hasEn && enVal) {
            setDeep(enJson, key.split('.'), enVal);
            enFlat[key] = enVal;
            addedToEn++;
        }
    }

    // 3. Reconcile remaining disparities between AR and EN (e.g. keys in one but not other)
    for (const key of Object.keys(enFlat)) {
        if (!(key in arFlat)) {
            const enVal = enFlat[key];
            const arVal = generateArabicFromKeyOrDefault(key, typeof enVal === 'string' ? enVal : '');
            setDeep(arJson, key.split('.'), arVal);
            arFlat[key] = arVal;
            addedToAr++;
        }
    }
    for (const key of Object.keys(arFlat)) {
        if (!(key in enFlat)) {
            const arVal = arFlat[key];
            const enVal = generateEnglishFromKeyOrDefault(key, typeof arVal === 'string' ? arVal : '');
            setDeep(enJson, key.split('.'), enVal);
            enFlat[key] = enVal;
            addedToEn++;
        }
    }

    fs.writeFileSync(arPath, JSON.stringify(arJson, null, 4) + '\n', 'utf8');
    fs.writeFileSync(enPath, JSON.stringify(enJson, null, 4) + '\n', 'utf8');

    console.log(`Updated translation files: added ${addedToAr} keys to AR, ${addedToEn} keys to EN.`);
    return { addedToAr, addedToEn };
}

function titleCaseFromKey(key) {
    const parts = key.split('.');
    const last = parts[parts.length - 1];
    return last
        .replace(/[_-]/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase());
}

const COMMON_DICTIONARY_AR_TO_EN = {
    'إلغاء': 'Cancel',
    'حفظ': 'Save',
    'تأكيد': 'Confirm',
    'إغلاق': 'Close',
    'رجوع': 'Back',
    'تعديل': 'Edit',
    'حذف': 'Delete',
    'إضافة': 'Add',
    'بحث': 'Search',
    'تحميل': 'Loading',
    'تفاصيل': 'Details',
    'الحالة': 'Status',
    'التاريخ': 'Date',
    'الوقت': 'Time',
    'المريض': 'Patient',
    'الطبيب': 'Doctor',
    'العيادة': 'Clinic',
    'الإجمالي': 'Total',
    'المستحق': 'Payable',
    'المدفوع': 'Paid',
    'المتبقي': 'Remaining',
    'الراتب': 'Salary',
    'المصروفات': 'Expenses',
    'الإيرادات': 'Revenue',
    'تقرير': 'Report',
    'التقارير': 'Reports',
    'مكتمل': 'Complete',
    'جزئي': 'Partial',
    'غير متاح': 'Unavailable',
    'خطأ': 'Error',
    'يوم': 'Day',
    'أيام': 'Days',
    'شهر': 'Month',
    'شهور': 'Months',
    'سنة': 'Year',
};

function generateEnglishFromKeyOrDefault(key, defaultText) {
    if (EXPLICIT_TRANSLATIONS[key]?.en) return EXPLICIT_TRANSLATIONS[key].en;

    // If defaultText is already ASCII / English
    if (defaultText && !/[\u0600-\u06FF]/.test(defaultText)) {
        return defaultText;
    }

    // Check common dictionary
    if (defaultText && COMMON_DICTIONARY_AR_TO_EN[defaultText]) {
        return COMMON_DICTIONARY_AR_TO_EN[defaultText];
    }

    // Derive from key
    const parts = key.split('.');
    const last = parts[parts.length - 1];
    const prev = parts.length > 1 ? parts[parts.length - 2] : '';

    if (last === 'title') return `${titleCaseFromKey(prev)} Title`;
    if (last === 'subtitle') return `${titleCaseFromKey(prev)} Subtitle`;
    if (last === 'desc' || last === 'description') return `${titleCaseFromKey(prev)} Description`;

    return titleCaseFromKey(key);
}

function generateArabicFromKeyOrDefault(key, defaultText) {
    if (EXPLICIT_TRANSLATIONS[key]?.ar) return EXPLICIT_TRANSLATIONS[key].ar;

    // If defaultText is already Arabic
    if (defaultText && /[\u0600-\u06FF]/.test(defaultText)) {
        return defaultText;
    }

    // Common English to Arabic fallback patterns
    const lower = (defaultText || '').toLowerCase().trim();
    if (lower === 'cancel') return 'إلغاء';
    if (lower === 'save' || lower === 'save changes') return 'حفظ';
    if (lower === 'confirm') return 'تأكيد';
    if (lower === 'close') return 'إغلاق';
    if (lower === 'delete') return 'حذف';
    if (lower === 'edit') return 'تعديل';
    if (lower === 'search') return 'بحث';
    if (lower === 'loading...') return 'جاري التحميل...';
    if (lower === 'details' || lower === 'view details') return 'التفاصيل';
    if (lower === 'status') return 'الحالة';
    if (lower === 'active') return 'نشط';
    if (lower === 'expired') return 'منتهي';
    if (lower === 'name') return 'الاسم';
    if (lower === 'email') return 'البريد الإلكتروني';
    if (lower === 'phone') return 'الهاتف';
    if (lower === 'date') return 'التاريخ';
    if (lower === 'notes') return 'ملاحظات';
    if (lower === 'actions') return 'إجراءات';
    if (lower === 'yes') return 'نعم';
    if (lower === 'no') return 'لا';

    const parts = key.split('.');
    const last = parts[parts.length - 1];

    if (last.includes('title')) return 'العنوان';
    if (last.includes('desc')) return 'الوصف';
    if (last.includes('save')) return 'حفظ';
    if (last.includes('cancel')) return 'إلغاء';
    if (last.includes('delete')) return 'حذف';
    if (last.includes('error')) return 'حدث خطأ';
    if (last.includes('success')) return 'تم بنجاح';

    return defaultText || key;
}

if (process.argv[1] === __filename) {
    buildAndApplyTranslations();
}
