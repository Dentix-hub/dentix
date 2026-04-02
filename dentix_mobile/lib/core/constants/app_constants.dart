class AppConstants {
  AppConstants._();

  // App Info
  static const String appName = 'Dentix';
  static const String appVersion = '1.0.0';

  // Durations
  static const Duration animationDuration = Duration(milliseconds: 300);
  static const Duration snackBarDuration = Duration(seconds: 3);
  static const Duration sessionTimeout = Duration(minutes: 30);
  static const Duration debounceDelay = Duration(milliseconds: 300);

  // Sizes
  static const double defaultPadding = 16.0;
  static const double smallPadding = 8.0;
  static const double largePadding = 24.0;
  static const double defaultRadius = 12.0;
  static const double cardElevation = 2.0;

  // Pagination
  static const int defaultPageSize = 20;
}
