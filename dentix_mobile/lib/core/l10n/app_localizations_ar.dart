// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Arabic (`ar`).
class AppLocalizationsAr extends AppLocalizations {
  AppLocalizationsAr([String locale = 'ar']) : super(locale);

  @override
  String get appTitle => 'دنتكس';

  @override
  String get login => 'تسجيل الدخول';

  @override
  String get email => 'البريد الإلكتروني';

  @override
  String get password => 'كلمة المرور';

  @override
  String get invalidEmail => 'البريد الإلكتروني غير صالح';

  @override
  String get invalidPassword => 'كلمة المرور يجب أن تكون 6 أحرف على الأقل';

  @override
  String get loginFailed => 'فشل تسجيل الدخول، يرجى التحقق من البيانات';

  @override
  String get dashboard => 'لوحة التحكم';

  @override
  String get patients => 'المرضى';

  @override
  String get appointments => 'المواعيد';

  @override
  String get more => 'المزيد';

  @override
  String get settings => 'الإعدادات';

  @override
  String get logout => 'تسجيل الخروج';

  @override
  String get search => 'بحث';

  @override
  String get loading => 'جاري التحميل...';

  @override
  String get error => 'حدث خطأ';

  @override
  String get retry => 'إعادة المحاولة';

  @override
  String get totalPatients => 'إجمالي المرضى';

  @override
  String get todayAppointments => 'مواعيد اليوم';

  @override
  String get todayRevenue => 'إيرادات اليوم';

  @override
  String get welcome => 'مرحباً بك في دنتكس';

  @override
  String get pleaseLogin => 'يرجى تسجيل الدخول للمتابعة';

  @override
  String get welcomeBack => 'مرحباً بعودتك!';

  @override
  String get noAppointmentsToday => 'لا توجد مواعيد اليوم';

  @override
  String get searchPatients => 'بحث عن مريض...';

  @override
  String get noPatientsFound => 'لم يتم العثور على مرضى';

  @override
  String get addFirstPatient => 'أضف أول مريض للبدء';

  @override
  String get addPatient => 'إضافة مريض';

  @override
  String get newAppointment => 'موعد جديد';

  @override
  String get calendarView => 'عرض التقويم';

  @override
  String get selectDate => 'حدد تاريخاً لعرض المواعيد';

  @override
  String get noAppointments => 'لا توجد مواعيد';

  @override
  String get tapToAddAppointment => 'اضغط على الزر لإضافة موعد';

  @override
  String get appearance => 'المظهر';

  @override
  String get darkMode => 'الوضع الليلي';

  @override
  String get language => 'اللغة';

  @override
  String get account => 'الحساب';

  @override
  String get changePassword => 'تغيير كلمة المرور';

  @override
  String get notifications => 'الإشعارات';

  @override
  String get about => 'حول التطبيق';

  @override
  String get version => 'الإصدار';

  @override
  String get helpSupport => 'المساعدة والدعم';

  @override
  String get cancel => 'إلغاء';

  @override
  String get confirmLogout => 'هل أنت متأكد من تسجيل الخروج؟';

  @override
  String get dentalManagement => 'نظام إدارة عيادات الأسنان';

  @override
  String get profile => 'الملف الشخصي';

  @override
  String get treatments => 'العلاجات';

  @override
  String get history => 'السجل';

  @override
  String get contactInfo => 'معلومات التواصل';

  @override
  String get personalInfo => 'المعلومات الشخصية';

  @override
  String get medicalInfo => 'المعلومات الطبية';

  @override
  String get medicalHistory => 'التاريخ الطبي';

  @override
  String get allergies => 'الحساسية';

  @override
  String get notAvailable => 'غير متوفر';

  @override
  String get noMedicalHistory => 'لا يوجد تاريخ طبي مسجل';

  @override
  String get noAllergies => 'لا يوجد حساسية مسجلة';

  @override
  String get noTreatments => 'لا توجد علاجات بعد';

  @override
  String get historyComingSoon => 'سجل المواعيد قريباً';

  @override
  String get themeSystem => 'افتراضي النظام';

  @override
  String get themeLight => 'فاتح';

  @override
  String get themeDark => 'داكن';

  @override
  String get theme => 'السمة';

  @override
  String get security => 'الأمان';

  @override
  String get financialOverview => 'Financial Overview';

  @override
  String get recordPayment => 'Record Payment';

  @override
  String get revenue => 'Revenue';

  @override
  String get expense => 'Expense';

  @override
  String get netIncome => 'Net Income';

  @override
  String transactionNumber(int number) {
    return 'Transaction #$number';
  }

  @override
  String get amount => 'Amount';

  @override
  String get date => 'Date';

  @override
  String get patientId => 'Patient ID';

  @override
  String get description => 'Description';

  @override
  String get requiredField => 'This field is required';

  @override
  String get invalidAmount => 'Please enter a valid amount';

  @override
  String get invalidNumber => 'Please enter a valid number';

  @override
  String get paymentRecorded => 'Payment recorded successfully';

  @override
  String get prescriptions => 'Prescriptions';

  @override
  String get createPrescription => 'Create Prescription';

  @override
  String get noPrescriptions => 'No prescriptions yet';

  @override
  String get medications => 'Medications';

  @override
  String get addMedication => 'Add Medication';

  @override
  String get medication => 'Medication';

  @override
  String get medicationId => 'Medication ID';

  @override
  String get dosage => 'Dosage';

  @override
  String get frequency => 'Frequency';

  @override
  String get duration => 'Duration';

  @override
  String get noMedicationsAdded => 'No medications added yet';

  @override
  String get addAtLeastOneMedication => 'Please add at least one medication';

  @override
  String get prescriptionCreated => 'Prescription created successfully';

  @override
  String get labOrders => 'Lab Orders';

  @override
  String get createLabOrder => 'Create Lab Order';

  @override
  String get noLabOrders => 'No lab orders yet';

  @override
  String get dueDate => 'Due Date';

  @override
  String get overdue => 'Overdue';

  @override
  String get all => 'All';

  @override
  String get statusPending => 'Pending';

  @override
  String get statusInProgress => 'In Progress';

  @override
  String get statusCompleted => 'Completed';

  @override
  String get statusCancelled => 'Cancelled';

  @override
  String get featureComingSoon => 'Coming soon';

  @override
  String patientNumber(int number) {
    return 'Patient #$number';
  }

  @override
  String get labName => 'Lab Name';

  @override
  String get workItems => 'Work Items';

  @override
  String get addWorkItem => 'Add Work Item';

  @override
  String get workItem => 'Work Item';

  @override
  String get workType => 'Work Type';

  @override
  String get quantity => 'Quantity';

  @override
  String get material => 'Material';

  @override
  String get shade => 'Shade';

  @override
  String get noWorkItemsAdded => 'No work items added yet';

  @override
  String get addAtLeastOneWorkItem => 'Please add at least one work item';

  @override
  String get labOrderCreated => 'Lab order created successfully';

  @override
  String get currentPassword => 'Current Password';

  @override
  String get newPassword => 'New Password';

  @override
  String get confirmPassword => 'Confirm Password';

  @override
  String get passwordTooShort => 'Password must be at least 6 characters';

  @override
  String get passwordsDoNotMatch => 'Passwords do not match';

  @override
  String get passwordChanged => 'Password changed successfully';

  @override
  String get passwordChangeFailed => 'Failed to change password';

  @override
  String get fullName => 'Full Name';

  @override
  String get phone => 'Phone Number';

  @override
  String get dateOfBirth => 'Date of Birth';

  @override
  String get gender => 'Gender';

  @override
  String get address => 'Address';

  @override
  String get notes => 'Notes';

  @override
  String get save => 'Save';

  @override
  String get male => 'Male';

  @override
  String get female => 'Female';

  @override
  String get appointmentCreated => 'تم إنشاء الموعد بنجاح';

  @override
  String get noInfoAvailable => 'لا توجد معلومات متاحة';
}
