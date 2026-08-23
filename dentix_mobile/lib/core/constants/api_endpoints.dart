class ApiEndpoints {
  ApiEndpoints._();

  static const String baseUrl = '/api/v1';

  // Auth — backend registers the auth package under /api/v1/auth.
  // The legacy /token, /logout and /refresh paths DO NOT exist server-side
  // (HIGH-07 route probe); these constants now match the live registry.
  static const String login = '$baseUrl/auth/token';
  static const String logout = '$baseUrl/auth/logout';
  static const String refresh = '$baseUrl/auth/refresh';
  static const String me = '$baseUrl/users/me';

  // Password changes go through the same PUT /users/me contract the web app
  // uses (UserUpdate.password) — a dedicated /change-password route was
  // never registered server-side.
  static const String changePassword = me;

  // Users
  static const String usersMe = '$baseUrl/users/me';

  // Dashboard
  static const String dashboardStats = '$baseUrl/stats/dashboard';
  static const String financeStats = '$baseUrl/stats/finance';

  // Patients
  static const String patients = '$baseUrl/patients';
  static String patientById(String id) => '$baseUrl/patients/$id';

  // Appointments
  static const String appointments = '$baseUrl/appointments';
  static String appointmentById(String id) => '$baseUrl/appointments/$id';

  // Treatments
  static String treatmentsByPatient(String patientId) =>
      '$baseUrl/treatments/$patientId';
  static const String treatments = '$baseUrl/treatments';

  // Financial — mapped to the real registry (HIGH-07):
  // - Overview composes GET /stats/dashboard (tenant totals) with
  //   GET /payments (paged items).
  // - Recording a payment posts the canonical PaymentCreate contract.
  static const String financialOverview = '$baseUrl/stats/dashboard';
  static const String paymentsList = '$baseUrl/payments';
  static const String recordPayment = '$baseUrl/payments';

  // Lab Orders
  static const String labOrders = '$baseUrl/lab-orders';

  // Medications
  static const String medications = '$baseUrl/medications';

  // Procedures
  static const String procedures = '$baseUrl/procedures';

  // Prescriptions
  static const String prescriptions = '$baseUrl/prescriptions';

  // Notifications
  static const String notifications = '$baseUrl/notifications';
}
