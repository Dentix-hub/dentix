import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:hive_flutter/hive_flutter.dart';

import 'app.dart';
import 'core/di/providers.dart';
import 'features/auth/presentation/controllers/auth_notifier.dart';

// Auth Feature Provider
final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(
    loginUseCase: ref.watch(loginUseCaseProvider),
    logoutUseCase: ref.watch(logoutUseCaseProvider),
    changePasswordUseCase: ref.watch(changePasswordUseCaseProvider),
  );
});

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Hive.initFlutter();

  runApp(const ProviderScope(child: DentixApp()));
}
