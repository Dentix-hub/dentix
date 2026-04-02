import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:hive_flutter/hive_flutter.dart';

/// Theme mode enum for persistence
enum ThemeModeOption {
  system,
  light,
  dark,
}

/// Provider for theme mode with persistence
final themeModeProvider = StateNotifierProvider<ThemeModeNotifier, ThemeMode>(
  (ref) => ThemeModeNotifier(),
);

/// Notifier that manages theme mode state and persists to Hive
class ThemeModeNotifier extends StateNotifier<ThemeMode> {
  static const String _boxName = 'settings';
  static const String _key = 'theme_mode';

  ThemeModeNotifier() : super(ThemeMode.system) {
    _loadTheme();
  }

  /// Load saved theme from Hive
  Future<void> _loadTheme() async {
    final box = await Hive.openBox<String>(_boxName);
    final savedTheme = box.get(_key);
    
    if (savedTheme != null) {
      state = _parseThemeMode(savedTheme);
    }
  }

  /// Set theme mode and persist to Hive
  Future<void> setThemeMode(ThemeMode mode) async {
    state = mode;
    final box = await Hive.openBox<String>(_boxName);
    await box.put(_key, mode.name);
  }

  /// Convert string to ThemeMode
  ThemeMode _parseThemeMode(String value) {
    return switch (value) {
      'light' => ThemeMode.light,
      'dark' => ThemeMode.dark,
      _ => ThemeMode.system,
    };
  }
}

/// Extension to get display name for theme mode
extension ThemeModeExtension on ThemeMode {
  /// English display name for debugging/logging only.
  /// Use [localizedKey] with AppLocalizations for UI display.
  String get displayName {
    return switch (this) {
      ThemeMode.system => 'System Default',
      ThemeMode.light => 'Light',
      ThemeMode.dark => 'Dark',
    };
  }

  /// Localization key for UI display.
  /// Use with AppLocalizations.of(context)!.themeSystem etc.
  String get localizedKey {
    return switch (this) {
      ThemeMode.system => 'themeSystem',
      ThemeMode.light => 'themeLight',
      ThemeMode.dark => 'themeDark',
    };
  }
}
