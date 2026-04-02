// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appTitle => 'Dentix';

  @override
  String get login => 'Login';

  @override
  String get email => 'Email';

  @override
  String get password => 'Password';

  @override
  String get invalidEmail => 'Invalid email address';

  @override
  String get invalidPassword => 'Password must be at least 6 characters';

  @override
  String get loginFailed => 'Login failed, please check your credentials';

  @override
  String get dashboard => 'Dashboard';

  @override
  String get patients => 'Patients';

  @override
  String get appointments => 'Appointments';

  @override
  String get more => 'More';

  @override
  String get settings => 'Settings';

  @override
  String get logout => 'Logout';

  @override
  String get search => 'Search';

  @override
  String get loading => 'Loading...';

  @override
  String get error => 'An error occurred';

  @override
  String get retry => 'Retry';

  @override
  String get totalPatients => 'Total Patients';

  @override
  String get todayAppointments => 'Today\'s Appointments';

  @override
  String get todayRevenue => 'Today\'s Revenue';

  @override
  String get welcome => 'Welcome to Dentix';

  @override
  String get pleaseLogin => 'Please login to continue';

  @override
  String get welcomeBack => 'Welcome back!';

  @override
  String get noAppointmentsToday => 'No appointments today';

  @override
  String get searchPatients => 'Search patients...';

  @override
  String get noPatientsFound => 'No patients found';

  @override
  String get addFirstPatient => 'Add your first patient to get started';

  @override
  String get addPatient => 'Add Patient';

  @override
  String get newAppointment => 'New Appointment';

  @override
  String get calendarView => 'Calendar View';

  @override
  String get selectDate => 'Select a date to view appointments';

  @override
  String get noAppointments => 'No appointments';

  @override
  String get tapToAddAppointment => 'Tap the button to add an appointment';

  @override
  String get appearance => 'Appearance';

  @override
  String get darkMode => 'Dark Mode';

  @override
  String get language => 'Language';

  @override
  String get account => 'Account';

  @override
  String get changePassword => 'Change Password';

  @override
  String get notifications => 'Notifications';

  @override
  String get about => 'About';

  @override
  String get version => 'Version';

  @override
  String get helpSupport => 'Help & Support';

  @override
  String get cancel => 'Cancel';

  @override
  String get confirmLogout => 'Are you sure you want to logout?';

  @override
  String get dentalManagement => 'Dental Clinic Management';

  @override
  String get profile => 'Profile';

  @override
  String get treatments => 'Treatments';

  @override
  String get history => 'History';

  @override
  String get contactInfo => 'Contact Information';

  @override
  String get personalInfo => 'Personal Information';

  @override
  String get medicalInfo => 'Medical Information';

  @override
  String get medicalHistory => 'Medical History';

  @override
  String get allergies => 'Allergies';

  @override
  String get notAvailable => 'N/A';

  @override
  String get noMedicalHistory => 'No medical history recorded';

  @override
  String get noAllergies => 'No allergies recorded';

  @override
  String get noTreatments => 'No treatments yet';

  @override
  String get historyComingSoon => 'Appointment history coming soon';

  @override
  String get themeSystem => 'System Default';

  @override
  String get themeLight => 'Light';

  @override
  String get themeDark => 'Dark';

  @override
  String get theme => 'Theme';

  @override
  String get security => 'Security';

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
  String get appointmentCreated => 'Appointment created successfully';

  @override
  String get noInfoAvailable => 'No information available';
}
