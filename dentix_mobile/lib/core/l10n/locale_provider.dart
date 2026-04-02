import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:hive_flutter/hive_flutter.dart';

/// Provider for locale/language with persistence
final localeProvider = StateNotifierProvider<LocaleNotifier, Locale>(
  (ref) => LocaleNotifier(),
);

/// Notifier that manages locale state and persists to Hive
class LocaleNotifier extends StateNotifier<Locale> {
  static const String _boxName = 'settings';
  static const String _key = 'locale';

  LocaleNotifier() : super(const Locale('en')) {
    _loadLocale();
  }

  /// Load saved locale from Hive
  Future<void> _loadLocale() async {
    final box = await Hive.openBox<String>(_boxName);
    final savedLocale = box.get(_key);
    
    if (savedLocale != null) {
      state = Locale(savedLocale);
    }
  }

  /// Set locale and persist to Hive
  Future<void> setLocale(String languageCode) async {
    state = Locale(languageCode);
    final box = await Hive.openBox<String>(_boxName);
    await box.put(_key, languageCode);
  }

  /// Toggle between English and Arabic
  Future<void> toggleLocale() async {
    final newLocale = state.languageCode == 'en' ? 'ar' : 'en';
    await setLocale(newLocale);
  }

  /// Get supported locales
  static List<Locale> get supportedLocales {
    return const [
      Locale('en'),
      Locale('ar'),
    ];
  }
}

/// Extension to get display name for language
extension LocaleExtension on Locale {
  String get displayName {
    return switch (languageCode) {
      'en' => 'English',
      'ar' => 'العربية',
      _ => languageCode,
    };
  }

  bool get isRTL => languageCode == 'ar';
}
