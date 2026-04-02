class ApiEndpoints {
  ApiEndpoints._();

  static const String baseUrl = '/api/v1';

  // Auth
  static const String login = '$baseUrl/token';
  static const String logout = '$baseUrl/logout';
  static const String refresh = '$baseUrl/refresh';
  static const String me = '$baseUrl/users/me';
  static const String changePassword = '$baseUrl/change-password';

  // Users
  static const String usersMe = '$baseUrl/users/me';

  // Dashboard
  static const String dashboardStats = '$baseUrl/stats/dashboard';
  static const String financeStats = '$baseUrl/stats/finance';

  // Patients
  static const String patients = '$baseUrl/patients/';
  static String patientById(String id) => '$baseUrl/patients/$id';

  // Appointments
  static const String appointments = '$baseUrl/appointments/';
  static String appointmentById(String id) => '$baseUrl/appointments/$id';

  // Treatments
  static String treatmentsByPatient(String patientId) =>
      '$baseUrl/treatments/$patientId';
  static const String treatments = '$baseUrl/treatments/';

  // Financial
  static const String financialOverview = '$baseUrl/financial/overview';
  static const String recordPayment = '$baseUrl/financial/record-payment';

  // Lab Orders
  static const String labOrders = '$baseUrl/lab-orders/';

  // Medications
  static const String medications = '$baseUrl/medications/';

  // Procedures
  static const String procedures = '$baseUrl/procedures/';

  // Prescriptions
  static const String prescriptions = '$baseUrl/prescriptions/';

  // Notifications
  static const String notifications = '$baseUrl/notifications/';
}
