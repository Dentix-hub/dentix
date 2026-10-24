import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');
const arPath = path.join(rootDir, 'src', 'locales', 'ar', 'translation.json');
const enPath = path.join(rootDir, 'src', 'locales', 'en', 'translation.json');

const arJson = JSON.parse(fs.readFileSync(arPath, 'utf8'));
const enJson = JSON.parse(fs.readFileSync(enPath, 'utf8'));

// Helper to set nested property in object without disrupting structure
function setNested(obj, pathStr, value) {
    const parts = pathStr.split('.');
    let curr = obj;
    for (let i = 0; i < parts.length - 1; i++) {
        if (!curr[parts[i]]) {
            curr[parts[i]] = {};
        }
        curr = curr[parts[i]];
    }
    curr[parts[parts.length - 1]] = value;
}

// 1. Quality translations for all (a) keys without Arabic letters and (b) generic fallbacks
const QUALITY_TRANSLATIONS = {
    // === (a) Keys that previously held English in AR ===
    'common.all': { ar: 'الكل', en: 'All' },
    'common.records': { ar: 'سجلات', en: 'records' },
    'common.page': { ar: 'صفحة', en: 'Page' },
    'common.of': { ar: 'من', en: 'of' },
    'common.none': { ar: 'لا يوجد', en: 'None' },
    'common.add': { ar: 'إضافة', en: 'Add' },
    'common.minutes_short': { ar: 'دقيقة', en: 'min' },
    'common.done': { ar: 'تم', en: 'Done' },
    'common.clear': { ar: 'مسح', en: 'Clear' },
    'common.pagination.label': { ar: 'التنقل بين الصفحات', en: 'Pagination' },
    'common.pagination.page': { ar: 'صفحة', en: 'Page' },
    'common.pagination.of': { ar: 'من', en: 'of' },
    'common.pagination.previous': { ar: 'السابق', en: 'Previous' },
    'common.pagination.next': { ar: 'التالي', en: 'Next' },
    'common.close_menu': { ar: 'إغلاق القائمة', en: 'Close menu' },
    'common.main_navigation': { ar: 'التنقل الرئيسي', en: 'Main navigation' },
    'common.toggle_sidebar': { ar: 'تبديل الشريط الجانبي', en: 'Toggle sidebar' },
    'common.open_menu': { ar: 'فتح القائمة', en: 'Open menu' },
    'common.processing': { ar: 'جاري المعالجة...', en: 'Processing...' },
    'common.unknown': { ar: 'غير معروف', en: 'Unknown' },
    'common.patient': { ar: 'المريض', en: 'Patient' },
    'common.time': { ar: 'الوقت', en: 'Time' },
    'common.amount': { ar: 'المبلغ', en: 'Amount' },
    'common.today': { ar: 'اليوم', en: 'Today' },
    'common.hour': { ar: 'ساعة', en: 'Hour' },
    'common.minute': { ar: 'دقيقة', en: 'Minute' },
    'common.search_min_chars': { ar: 'اكتب حرفين على الأقل للبحث', en: 'Type at least 2 characters to search' },

    'patients.form.name_required': { ar: 'اسم المريض مطلوب', en: 'Patient name is required' },
    'patients.form.name': { ar: 'اسم المريض', en: 'Patient Name' },
    'patients.form.phone': { ar: 'رقم الهاتف', en: 'Phone Number' },
    'patients.form.create_btn': { ar: 'إنشاء واختيار', en: 'Create & Select' },
    'patients.workspace_search_placeholder': { ar: 'البحث بالاسم، رقم الملف، أو الهاتف...', en: 'Search by name, file number, or phone...' },
    'patients.workspace_search_label': { ar: 'بحث المرضى', en: 'Search patients' },
    'patients.workspace_search_hint': { ar: 'يدعم تنويعات الأسماء العربية وتنسيقات الهاتف المصرية.', en: 'Arabic name variants and Egyptian phone formats are supported.' },
    'patients.quick_filters': { ar: 'تصفية المرضى', en: 'Patient filters' },
    'patients.call_patient': { ar: 'الاتصال بالمريض', en: 'Call Patient' },
    'patients.whatsapp_patient': { ar: 'مراسلة المريض عبر واتساب', en: 'Message on WhatsApp' },
    'patients.new_appointment': { ar: 'موعد جديد', en: 'New Appointment' },
    'patients.open_patient': { ar: 'فتح ملف المريض', en: 'Open Patient File' },
    'patients.archive_patient': { ar: 'أرشفة المريض', en: 'Archive Patient' },
    'patients.no_search_results': { ar: 'لا توجد نتائج مطابقة للبحث', en: 'No matching patients found' },
    'patients.no_search_results_hint': { ar: 'تأكد من كتابة الاسم أو رقم الهاتف بشكل صحيح', en: 'Check the spelling of the name or phone number' },
    'patients.assigned_doctor': { ar: 'الطبيب المعالج', en: 'Assigned Doctor' },
    'patients.load_more': { ar: 'تحميل المزيد', en: 'Load More' },
    'patients.exact_dob_known': { ar: 'تاريخ الميلاد الدقيق معروف', en: 'Exact date of birth is known' },
    'patients.date_of_birth': { ar: 'تاريخ الميلاد', en: 'Date of Birth' },
    'patients.dob_hint': { ar: 'أدخل تاريخ الميلاد الدقيق لحساب العمر تلقائيًا', en: 'Enter exact date of birth to calculate age' },
    'patients.fast_registration': { ar: 'تسجيل سريع', en: 'Fast Registration' },
    'patients.possible_matches': { ar: 'مرضى مطابقون محتملون', en: 'Possible Matches' },
    'patients.possible_matches_hint': { ar: 'قد يكون المريض مسجلاً مسبقًا برقم هاتف أو اسم مشابه', en: 'Patient may already exist with similar details' },
    'patients.additional_information': { ar: 'معلومات إضافية', en: 'Additional Information' },
    'patients.messages.name_required': { ar: 'اسم المريض مطلوب', en: 'Patient name is required' },
    'patients.messages.creating': { ar: 'جاري إنشاء ملف المريض...', en: 'Creating patient...' },
    'patients.years_short': { ar: 'سنة', en: 'y' },

    'appointments.view.label': { ar: 'عرض المواعيد', en: 'Appointment view' },
    'appointments.request_dismissed': { ar: 'تم تجاهل طلب الزيارة القادمة', en: 'Next-visit request dismissed' },
    'appointments.board.swipe_hint': { ar: 'اسحب أفقيًا للتنقل بين المراحل، أو غيّر الحالة من البطاقة مباشرة.', en: 'Swipe horizontally to view stages, or update status directly from each card.' },
    'appointments.drag_handle': { ar: 'سحب الموعد', en: 'Drag appointment' },

    'language.code': { ar: 'ar', en: 'en' },

    'inventory.actions.more': { ar: 'المزيد من إجراءات المواد', en: 'More material actions' },
    'inventory.filters.label': { ar: 'تصفية المخزون', en: 'Filter stock' },
    'billing.expenses.categories.laboratory': { ar: 'المعمل', en: 'Laboratory' },
    'billing.expenses.notes_placeholder': { ar: 'ملاحظات المصروفات (اختياري)...', en: 'Optional expense notes...' },
    'notifications.empty': { ar: 'لا توجد إشعارات جديدة', en: 'No new notifications' },
    'notifications.dismiss': { ar: 'تجاهل الإشعار', en: 'Dismiss notification' },
    'notifications.new': { ar: 'جديد', en: 'New' },

    'care_sessions.continue_treatment': { ar: 'متابعة العلاج', en: 'Continue Treatment' },
    'care_sessions.tooth': { ar: 'السن', en: 'Tooth' },
    'care_sessions.status_paused': { ar: 'جلسة متوقفة مؤقتًا', en: 'Paused Session' },
    'care_sessions.status_in_progress': { ar: 'قيد التنفيذ', en: 'In Progress' },
    'care_sessions.steps_progress': { ar: 'تم إنجاز {{completed}} من أصل {{total}} خطوات ({{percent}}%)', en: '{{completed}} of {{total}} steps completed ({{percent}}%)' },
    'care_sessions.next_step': { ar: 'التالي: {{step}}', en: 'Next: {{step}}' },
    'care_sessions.ready_to_resume': { ar: 'العلاج جاهز للاستئناف على كرسي العلاج', en: 'Treatment ready to be resumed chairside' },
    'care_sessions.canals': { ar: 'القنوات العصبية', en: 'Canals' },
    'care_sessions.resume_session': { ar: 'استئناف الجلسة', en: 'Resume Session' },
    'care_sessions.resume_treatment': { ar: 'استئناف العلاج', en: 'Resume Treatment' },
    'care_sessions.canal_lengths': { ar: 'القنوات المسجلة:', en: 'Recorded Canals:' },
    'care_sessions.last_visit': { ar: 'آخر زيارة:', en: 'Last visit:' },
    'care_sessions.measurements_detail': { ar: 'ملاحظات وقياسات القنوات العصبية:', en: 'Canal Observations & Measurements:' },

    'lab_handoff.failed_load_labs': { ar: 'تعذر تحميل قائمة معامل الأسنان.', en: 'Failed to load dental laboratories list.' },
    'lab_handoff.no_double_billing': { ar: '0 رسوم مكررة (R06)', en: '0 Duplicate Billing (R06)' },
    'lab_handoff.laboratory_label': { ar: 'اختر معمل الأسنان', en: 'Select Dental Laboratory' },
    'lab_handoff.choose_lab': { ar: '-- اختر المعمل --', en: '-- Select Laboratory --' },
    'lab_handoff.tooth_number': { ar: 'رقم السن', en: 'Tooth Number' },
    'lab_handoff.work_type': { ar: 'نوع التركيبة / العمل المطلوب', en: 'Prescription / Work Type' },
    'lab_handoff.shade_label': { ar: 'اختيار درجة اللون (Shade)', en: 'Shade Selection' },
    'lab_handoff.custom_shade': { ar: 'درجة لون أخرى...', en: 'Other shade...' },
    'lab_handoff.material_label': { ar: 'الخامة / المادة', en: 'Material' },
    'lab_handoff.custom_material': { ar: 'خامة أخرى...', en: 'Other material...' },
    'lab_handoff.delivery_date': { ar: 'موعد التسليم المتوقع', en: 'Expected Delivery Date' },
    'lab_handoff.lab_cost': { ar: 'تكلفة المعمل', en: 'Lab Cost' },
    'lab_handoff.patient_price': { ar: 'سعر المريض (استرشادي)', en: 'Patient Price (Estimated)' },
    'lab_handoff.notes_label': { ar: 'تعليمات لفني المعمل', en: 'Instructions to Lab Technician' },
    'lab_handoff.notes_placeholder': { ar: 'مثال: حافة تحت اللثة على السطح الدهليزي، فحص نقطة التماس مع سن 22...', en: 'e.g. Subgingival margin on buccal, check contact with tooth 22...' },
    'lab_handoff.submitting': { ar: 'جاري الإرسال للمعمل...', en: 'Dispatching to lab...' },
    'lab_handoff.submit_button': { ar: 'إرسال للمعمل (بنقرة واحدة)', en: 'Send to Lab (1-Tap)' },

    'nav.home': { ar: 'الرئيسية', en: 'Home' },
    'nav.settings': { ar: 'إدارة تفضيلات وإعدادات التطبيق', en: 'Manage application preferences' },

    // === (b) Specific Arabic for generic fallbacks ===
    'common.error_occurred': { ar: 'حدث خطأ أثناء حفظ الإعدادات', en: 'An error occurred while saving settings' },
    'patients.load_error': { ar: 'حدث خطأ أثناء تحميل بيانات المرضى', en: 'Failed to load patient records' },
    'patients.load_error_hint': { ar: 'تعذر تحميل سجلات المرضى. يرجى تحديث الصفحة والمحاولة مرة أخرى.', en: 'Failed to load patient records. Please refresh and try again.' },
    'patients.update_success': { ar: 'تم تحديث بيانات المريض بنجاح', en: 'Patient updated successfully' },
    'patients.messages.create_success': { ar: 'تم إنشاء ملف المريض بنجاح', en: 'Patient created successfully' },
    'patients.messages.create_error': { ar: 'فشل إنشاء ملف المريض', en: 'Failed to create patient' },
    'patient_details.chart_error': { ar: 'تعذر تحميل مساحة العمل ومخطط الأسنان السريري', en: 'Failed to load clinical workspace and chart' },
    'inventory.track_session.messages.success_close': { ar: 'تم تسجيل استهلاك الجلسة وإغلاقها بنجاح', en: 'Session consumption recorded and closed successfully' },
    'super_admin.backup.oauth_error': { ar: 'حدث خطأ أثناء المصادقة عبر Google OAuth', en: 'An error occurred during Google OAuth authentication' },
    'lab_handoff.error_select_lab': { ar: 'من فضلك اختر المعمل', en: 'Please select a laboratory.' },
    'lab_handoff.error_submitting': { ar: 'فشل إرسال طلب المعمل', en: 'Failed to dispatch lab handoff.' },
    'lab_handoff.success_detail': { ar: 'تم إنشاء طلب المعمل وربطه بالجلسة بنجاح', en: 'Lab order created and linked to session successfully' },

    // === (c) Proper English phrases for humanized keys in clinic screens ===
    'common.saving': { ar: 'جاري الحفظ...', en: 'Saving...' },
    'common.searching': { ar: 'جاري البحث...', en: 'Searching...' },
    'common.deleting': { ar: 'جاري الحذف...', en: 'Deleting...' },
    'common.no_data': { ar: 'لا توجد بيانات للعرض', en: 'No data available to display' },
    'common.try_again_later': { ar: 'يرجى المحاولة مرة أخرى أو التحقق من الاتصال', en: 'Please try again later or check connection' },
    'common.showing_results': { ar: 'عرض {{from}} إلى {{to}} من أصل {{total}} سجل', en: 'Showing {{from}} to {{to}} of {{total}} records' },
    'common.prev_page': { ar: 'الصفحة السابقة', en: 'Previous page' },
    'common.next_page': { ar: 'الصفحة التالية', en: 'Next page' },
    'common.clear_search': { ar: 'مسح البحث', en: 'Clear search' },
    'common.reset_filters': { ar: 'إعادة ضبط الفلاتر', en: 'Reset filters' },
    'common.active_filters': { ar: 'الفلاتر النشطة:', en: 'Active filters:' },
    'common.search_for': { ar: 'بحث عن:', en: 'Search for:' },
    'common.remove_search_filter': { ar: 'إزالة فلتر البحث', en: 'Remove search filter' },
    'common.remove_filter': { ar: 'إزالة الفلتر', en: 'Remove filter' },
    'common.view_all': { ar: 'عرض الكل', en: 'View all' },
    'common.view_details': { ar: 'عرض التفاصيل', en: 'View details' },
    'common.prev_month': { ar: 'الشهر السابق', en: 'Previous month' },
    'common.next_month': { ar: 'الشهر التالي', en: 'Next month' },
    'common.delete_success': { ar: 'تم الحذف بنجاح', en: 'Deleted successfully' },
    'patients.file_number': { ar: 'رقم الملف', en: 'File Number' },
    'patients.full_record': { ar: 'الملف الطبي والمالي الكامل', en: 'Complete Medical & Financial Record' },
    'patients.view_timeline': { ar: 'عرض سجل المريض الكامل', en: 'View Patient Timeline' },
    'patients.view_profile': { ar: 'عرض ملف المريض', en: 'View Patient Profile' },
    'appointments.treatments_count': { ar: 'إجراء علاجي', en: 'Treatments Count' },
    'appointments.no_treatments_period': { ar: 'لا توجد علاجات منفذة لهذا الطبيب في هذه الفترة', en: 'No treatments performed for this doctor in this period' },
    'appointments.confirm_delete_desc': { ar: 'هل أنت متأكد من حذف هذا الموعد؟ هذه العملية لا يمكن التراجع عنها.', en: 'Are you sure you want to delete this appointment? This action cannot be undone.' },
    'settings.price_lists.deactivated_success': { ar: 'تم تعطيل قائمة الأسعار بنجاح', en: 'Price list deactivated successfully' },
    'settings.price_lists.deactivate_title': { ar: 'تعطيل قائمة الأسعار', en: 'Deactivate Price List' },
    'settings.price_lists.deactivate_btn': { ar: 'تعطيل', en: 'Deactivate' },
    'inventory.alerts.more_alerts': { ar: 'تنبيهات إضافية', en: 'Additional alerts' },
    'inventory.actions.add_warehouse': { ar: 'إضافة مخزن جديد', en: 'Add New Warehouse' },
    'inventory.messages.load_error': { ar: 'حدث خطأ في تحميل البيانات', en: 'Failed to load inventory data' },
    'inventory.warehouses.add_success': { ar: 'تم إضافة المخزن بنجاح', en: 'Warehouse added successfully' },
    'inventory.warehouses.add_fail': { ar: 'فشل إضافة المخزن', en: 'Failed to add warehouse' },
    'inventory.warehouses.add_title': { ar: 'إضافة مخزن جديد', en: 'Add New Warehouse' },
    'inventory.warehouses.name_placeholder': { ar: 'مثال: المخزن الرئيسي', en: 'e.g. Main Clinic Store' },
    'inventory.warehouses.type_main': { ar: 'مخزن رئيسي (Main Warehouse)', en: 'Main Warehouse' },
    'inventory.warehouses.type_clinic': { ar: 'عيادة / فرعي (Clinic)', en: 'Clinic / Sub-store' },
    'inventory.track_session.info_close_auto': { ar: 'عند إنهاء الجلسة، سيتم حساب الاستهلاك تلقائياً بناءً على الأوزان النسبية للإجراءات.', en: 'Upon ending session, consumption is computed automatically based on procedure relative weights.' },
    'billing.expenses.notes': { ar: 'ملاحظات الصرف', en: 'Expense Notes' },
    'billing.payment_received': { ar: 'تم استلام الدفعة', en: 'Payment Received' },
    'insurance.deactivated_success': { ar: 'تم تعطيل شركة التأمين بنجاح', en: 'Insurance provider deactivated successfully' },
    'insurance.deactivate_title': { ar: 'تعطيل شركة التأمين', en: 'Deactivate Insurance Provider' },
    'insurance.deactivate_confirm': { ar: 'هل أنت متأكد من تعطيل شركة التأمين هذه؟', en: 'Are you sure you want to deactivate this insurance provider?' },
    'insurance.deactivate_btn': { ar: 'تعطيل', en: 'Deactivate' },
    'super_admin.backup.title': { ar: 'النسخ الاحتياطي السحابي', en: 'Cloud Backup' },
    'super_admin.backup.desc': { ar: 'إدارة وتكوين النسخ الاحتياطي التلقائي إلى Google Drive', en: 'Manage and configure automated backups to Google Drive' },
    'super_admin.backup.tab_status': { ar: 'حالة النسخ', en: 'Backup Status' },
    'super_admin.backup.tab_logs': { ar: 'سجلات العمليات', en: 'Operation Logs' },
    'super_admin.backup.tab_config': { ar: 'إعدادات المزامنة', en: 'Sync Configuration' },
    'super_admin.backup.tab_restore': { ar: 'الاستعادة من السحاب', en: 'Cloud Restore' },
};

let applied = 0;
for (const [key, val] of Object.entries(QUALITY_TRANSLATIONS)) {
    if (val.ar) {
        setNested(arJson, key, val.ar);
    }
    if (val.en) {
        setNested(enJson, key, val.en);
    }
    applied++;
}

fs.writeFileSync(arPath, JSON.stringify(arJson, null, 4) + '\n', 'utf8');
fs.writeFileSync(enPath, JSON.stringify(enJson, null, 4) + '\n', 'utf8');

console.log(`Successfully applied ${applied} high-quality translations across AR and EN!`);
