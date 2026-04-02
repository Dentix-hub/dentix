import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_ar.dart';
import 'app_localizations_en.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('ar'),
    Locale('en'),
  ];

  /// App title
  ///
  /// In en, this message translates to:
  /// **'Dentix'**
  String get appTitle;

  /// Login button text
  ///
  /// In en, this message translates to:
  /// **'Login'**
  String get login;

  /// Email field label
  ///
  /// In en, this message translates to:
  /// **'Email'**
  String get email;

  /// Password field label
  ///
  /// In en, this message translates to:
  /// **'Password'**
  String get password;

  /// Invalid email error
  ///
  /// In en, this message translates to:
  /// **'Invalid email address'**
  String get invalidEmail;

  /// Invalid password error
  ///
  /// In en, this message translates to:
  /// **'Password must be at least 6 characters'**
  String get invalidPassword;

  /// Login failed error
  ///
  /// In en, this message translates to:
  /// **'Login failed, please check your credentials'**
  String get loginFailed;

  /// Dashboard title
  ///
  /// In en, this message translates to:
  /// **'Dashboard'**
  String get dashboard;

  /// Patients title
  ///
  /// In en, this message translates to:
  /// **'Patients'**
  String get patients;

  /// Appointments title
  ///
  /// In en, this message translates to:
  /// **'Appointments'**
  String get appointments;

  /// More tab label
  ///
  /// In en, this message translates to:
  /// **'More'**
  String get more;

  /// Settings title
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get settings;

  /// Logout button
  ///
  /// In en, this message translates to:
  /// **'Logout'**
  String get logout;

  /// Search hint
  ///
  /// In en, this message translates to:
  /// **'Search'**
  String get search;

  /// Loading text
  ///
  /// In en, this message translates to:
  /// **'Loading...'**
  String get loading;

  /// Error message
  ///
  /// In en, this message translates to:
  /// **'An error occurred'**
  String get error;

  /// Retry button label
  ///
  /// In en, this message translates to:
  /// **'Retry'**
  String get retry;

  /// Total patients stat
  ///
  /// In en, this message translates to:
  /// **'Total Patients'**
  String get totalPatients;

  /// Today's appointments stat
  ///
  /// In en, this message translates to:
  /// **'Today\'s Appointments'**
  String get todayAppointments;

  /// Today's revenue stat
  ///
  /// In en, this message translates to:
  /// **'Today\'s Revenue'**
  String get todayRevenue;

  /// Welcome message
  ///
  /// In en, this message translates to:
  /// **'Welcome to Dentix'**
  String get welcome;

  /// Please login message
  ///
  /// In en, this message translates to:
  /// **'Please login to continue'**
  String get pleaseLogin;

  /// Welcome back message
  ///
  /// In en, this message translates to:
  /// **'Welcome back!'**
  String get welcomeBack;

  /// No appointments today message
  ///
  /// In en, this message translates to:
  /// **'No appointments today'**
  String get noAppointmentsToday;

  /// Search patients hint
  ///
  /// In en, this message translates to:
  /// **'Search patients...'**
  String get searchPatients;

  /// No patients found message
  ///
  /// In en, this message translates to:
  /// **'No patients found'**
  String get noPatientsFound;

  /// Add first patient message
  ///
  /// In en, this message translates to:
  /// **'Add your first patient to get started'**
  String get addFirstPatient;

  /// Add patient button
  ///
  /// In en, this message translates to:
  /// **'Add Patient'**
  String get addPatient;

  /// New appointment button
  ///
  /// In en, this message translates to:
  /// **'New Appointment'**
  String get newAppointment;

  /// Calendar view title
  ///
  /// In en, this message translates to:
  /// **'Calendar View'**
  String get calendarView;

  /// Select date instructions
  ///
  /// In en, this message translates to:
  /// **'Select a date to view appointments'**
  String get selectDate;

  /// No appointments message
  ///
  /// In en, this message translates to:
  /// **'No appointments'**
  String get noAppointments;

  /// Tap to add appointment instructions
  ///
  /// In en, this message translates to:
  /// **'Tap the button to add an appointment'**
  String get tapToAddAppointment;

  /// Appearance section title
  ///
  /// In en, this message translates to:
  /// **'Appearance'**
  String get appearance;

  /// Dark mode switch
  ///
  /// In en, this message translates to:
  /// **'Dark Mode'**
  String get darkMode;

  /// Language setting label
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get language;

  /// Account section title
  ///
  /// In en, this message translates to:
  /// **'Account'**
  String get account;

  /// Change password option
  ///
  /// In en, this message translates to:
  /// **'Change Password'**
  String get changePassword;

  /// Notifications setting
  ///
  /// In en, this message translates to:
  /// **'Notifications'**
  String get notifications;

  /// About section title
  ///
  /// In en, this message translates to:
  /// **'About'**
  String get about;

  /// Version label
  ///
  /// In en, this message translates to:
  /// **'Version'**
  String get version;

  /// Help and support setting
  ///
  /// In en, this message translates to:
  /// **'Help & Support'**
  String get helpSupport;

  /// Cancel button
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get cancel;

  /// Logout confirmation message
  ///
  /// In en, this message translates to:
  /// **'Are you sure you want to logout?'**
  String get confirmLogout;

  /// App subtitle
  ///
  /// In en, this message translates to:
  /// **'Dental Clinic Management'**
  String get dentalManagement;

  /// Profile tab label
  ///
  /// In en, this message translates to:
  /// **'Profile'**
  String get profile;

  /// Treatments tab label
  ///
  /// In en, this message translates to:
  /// **'Treatments'**
  String get treatments;

  /// History tab label
  ///
  /// In en, this message translates to:
  /// **'History'**
  String get history;

  /// Contact information section
  ///
  /// In en, this message translates to:
  /// **'Contact Information'**
  String get contactInfo;

  /// Personal information section
  ///
  /// In en, this message translates to:
  /// **'Personal Information'**
  String get personalInfo;

  /// Medical information section
  ///
  /// In en, this message translates to:
  /// **'Medical Information'**
  String get medicalInfo;

  /// Medical history label
  ///
  /// In en, this message translates to:
  /// **'Medical History'**
  String get medicalHistory;

  /// Allergies label
  ///
  /// In en, this message translates to:
  /// **'Allergies'**
  String get allergies;

  /// Not available text
  ///
  /// In en, this message translates to:
  /// **'N/A'**
  String get notAvailable;

  /// No medical history message
  ///
  /// In en, this message translates to:
  /// **'No medical history recorded'**
  String get noMedicalHistory;

  /// No allergies message
  ///
  /// In en, this message translates to:
  /// **'No allergies recorded'**
  String get noAllergies;

  /// No treatments message
  ///
  /// In en, this message translates to:
  /// **'No treatments yet'**
  String get noTreatments;

  /// History tab placeholder
  ///
  /// In en, this message translates to:
  /// **'Appointment history coming soon'**
  String get historyComingSoon;

  /// System theme option
  ///
  /// In en, this message translates to:
  /// **'System Default'**
  String get themeSystem;

  /// Light theme option
  ///
  /// In en, this message translates to:
  /// **'Light'**
  String get themeLight;

  /// Dark theme option
  ///
  /// In en, this message translates to:
  /// **'Dark'**
  String get themeDark;

  /// Theme setting label
  ///
  /// In en, this message translates to:
  /// **'Theme'**
  String get theme;

  /// Security section label
  ///
  /// In en, this message translates to:
  /// **'Security'**
  String get security;

  /// Financial overview page title
  ///
  /// In en, this message translates to:
  /// **'Financial Overview'**
  String get financialOverview;

  /// Record payment button
  ///
  /// In en, this message translates to:
  /// **'Record Payment'**
  String get recordPayment;

  /// Revenue label
  ///
  /// In en, this message translates to:
  /// **'Revenue'**
  String get revenue;

  /// Expense label
  ///
  /// In en, this message translates to:
  /// **'Expense'**
  String get expense;

  /// Net income label
  ///
  /// In en, this message translates to:
  /// **'Net Income'**
  String get netIncome;

  /// Transaction number label
  ///
  /// In en, this message translates to:
  /// **'Transaction #{number}'**
  String transactionNumber(int number);

  /// Amount field label
  ///
  /// In en, this message translates to:
  /// **'Amount'**
  String get amount;

  /// Date field label
  ///
  /// In en, this message translates to:
  /// **'Date'**
  String get date;

  /// Patient ID field label
  ///
  /// In en, this message translates to:
  /// **'Patient ID'**
  String get patientId;

  /// Description field label
  ///
  /// In en, this message translates to:
  /// **'Description'**
  String get description;

  /// Required field error message
  ///
  /// In en, this message translates to:
  /// **'This field is required'**
  String get requiredField;

  /// Invalid amount error message
  ///
  /// In en, this message translates to:
  /// **'Please enter a valid amount'**
  String get invalidAmount;

  /// Invalid number error message
  ///
  /// In en, this message translates to:
  /// **'Please enter a valid number'**
  String get invalidNumber;

  /// Payment recorded success message
  ///
  /// In en, this message translates to:
  /// **'Payment recorded successfully'**
  String get paymentRecorded;

  /// Prescriptions page title
  ///
  /// In en, this message translates to:
  /// **'Prescriptions'**
  String get prescriptions;

  /// Create prescription button
  ///
  /// In en, this message translates to:
  /// **'Create Prescription'**
  String get createPrescription;

  /// No prescriptions message
  ///
  /// In en, this message translates to:
  /// **'No prescriptions yet'**
  String get noPrescriptions;

  /// Medications section label
  ///
  /// In en, this message translates to:
  /// **'Medications'**
  String get medications;

  /// Add medication button
  ///
  /// In en, this message translates to:
  /// **'Add Medication'**
  String get addMedication;

  /// Medication label
  ///
  /// In en, this message translates to:
  /// **'Medication'**
  String get medication;

  /// Medication ID field label
  ///
  /// In en, this message translates to:
  /// **'Medication ID'**
  String get medicationId;

  /// Dosage field label
  ///
  /// In en, this message translates to:
  /// **'Dosage'**
  String get dosage;

  /// Frequency field label
  ///
  /// In en, this message translates to:
  /// **'Frequency'**
  String get frequency;

  /// Duration field label
  ///
  /// In en, this message translates to:
  /// **'Duration'**
  String get duration;

  /// No medications message
  ///
  /// In en, this message translates to:
  /// **'No medications added yet'**
  String get noMedicationsAdded;

  /// Add medication validation message
  ///
  /// In en, this message translates to:
  /// **'Please add at least one medication'**
  String get addAtLeastOneMedication;

  /// Prescription created success message
  ///
  /// In en, this message translates to:
  /// **'Prescription created successfully'**
  String get prescriptionCreated;

  /// Lab orders page title
  ///
  /// In en, this message translates to:
  /// **'Lab Orders'**
  String get labOrders;

  /// Create lab order button
  ///
  /// In en, this message translates to:
  /// **'Create Lab Order'**
  String get createLabOrder;

  /// No lab orders message
  ///
  /// In en, this message translates to:
  /// **'No lab orders yet'**
  String get noLabOrders;

  /// Due date label
  ///
  /// In en, this message translates to:
  /// **'Due Date'**
  String get dueDate;

  /// Overdue badge label
  ///
  /// In en, this message translates to:
  /// **'Overdue'**
  String get overdue;

  /// All filter option
  ///
  /// In en, this message translates to:
  /// **'All'**
  String get all;

  /// Pending status label
  ///
  /// In en, this message translates to:
  /// **'Pending'**
  String get statusPending;

  /// In Progress status label
  ///
  /// In en, this message translates to:
  /// **'In Progress'**
  String get statusInProgress;

  /// Completed status label
  ///
  /// In en, this message translates to:
  /// **'Completed'**
  String get statusCompleted;

  /// Cancelled status label
  ///
  /// In en, this message translates to:
  /// **'Cancelled'**
  String get statusCancelled;

  /// Feature coming soon message
  ///
  /// In en, this message translates to:
  /// **'Coming soon'**
  String get featureComingSoon;

  /// Patient number label
  ///
  /// In en, this message translates to:
  /// **'Patient #{number}'**
  String patientNumber(int number);

  /// Lab name field label
  ///
  /// In en, this message translates to:
  /// **'Lab Name'**
  String get labName;

  /// Work items section label
  ///
  /// In en, this message translates to:
  /// **'Work Items'**
  String get workItems;

  /// Add work item button
  ///
  /// In en, this message translates to:
  /// **'Add Work Item'**
  String get addWorkItem;

  /// Work item label
  ///
  /// In en, this message translates to:
  /// **'Work Item'**
  String get workItem;

  /// Work type field label
  ///
  /// In en, this message translates to:
  /// **'Work Type'**
  String get workType;

  /// Quantity field label
  ///
  /// In en, this message translates to:
  /// **'Quantity'**
  String get quantity;

  /// Material field label
  ///
  /// In en, this message translates to:
  /// **'Material'**
  String get material;

  /// Shade field label
  ///
  /// In en, this message translates to:
  /// **'Shade'**
  String get shade;

  /// No work items message
  ///
  /// In en, this message translates to:
  /// **'No work items added yet'**
  String get noWorkItemsAdded;

  /// Add work item validation message
  ///
  /// In en, this message translates to:
  /// **'Please add at least one work item'**
  String get addAtLeastOneWorkItem;

  /// Lab order created success message
  ///
  /// In en, this message translates to:
  /// **'Lab order created successfully'**
  String get labOrderCreated;

  /// Current password field label
  ///
  /// In en, this message translates to:
  /// **'Current Password'**
  String get currentPassword;

  /// New password field label
  ///
  /// In en, this message translates to:
  /// **'New Password'**
  String get newPassword;

  /// Confirm password field label
  ///
  /// In en, this message translates to:
  /// **'Confirm Password'**
  String get confirmPassword;

  /// Password too short error message
  ///
  /// In en, this message translates to:
  /// **'Password must be at least 6 characters'**
  String get passwordTooShort;

  /// Passwords do not match error message
  ///
  /// In en, this message translates to:
  /// **'Passwords do not match'**
  String get passwordsDoNotMatch;

  /// Password changed success message
  ///
  /// In en, this message translates to:
  /// **'Password changed successfully'**
  String get passwordChanged;

  /// Password change failed message
  ///
  /// In en, this message translates to:
  /// **'Failed to change password'**
  String get passwordChangeFailed;

  /// Full name label
  ///
  /// In en, this message translates to:
  /// **'Full Name'**
  String get fullName;

  /// Phone number label
  ///
  /// In en, this message translates to:
  /// **'Phone Number'**
  String get phone;

  /// Date of birth label
  ///
  /// In en, this message translates to:
  /// **'Date of Birth'**
  String get dateOfBirth;

  /// Gender label
  ///
  /// In en, this message translates to:
  /// **'Gender'**
  String get gender;

  /// Address label
  ///
  /// In en, this message translates to:
  /// **'Address'**
  String get address;

  /// Notes label
  ///
  /// In en, this message translates to:
  /// **'Notes'**
  String get notes;

  /// Save button
  ///
  /// In en, this message translates to:
  /// **'Save'**
  String get save;

  /// Male gender option
  ///
  /// In en, this message translates to:
  /// **'Male'**
  String get male;

  /// Female gender option
  ///
  /// In en, this message translates to:
  /// **'Female'**
  String get female;

  /// Appointment created success message
  ///
  /// In en, this message translates to:
  /// **'Appointment created successfully'**
  String get appointmentCreated;

  /// No information available message
  ///
  /// In en, this message translates to:
  /// **'No information available'**
  String get noInfoAvailable;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['ar', 'en'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'ar':
      return AppLocalizationsAr();
    case 'en':
      return AppLocalizationsEn();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
