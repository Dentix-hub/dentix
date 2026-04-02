import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

import '../../domain/entities/user_entity.dart';
import '../../domain/usecases/change_password.dart';
import '../../domain/usecases/login_usecase.dart';
import '../../domain/usecases/logout_usecase.dart';

part 'auth_notifier.freezed.dart';

@freezed
class AuthState with _$AuthState {
  const factory AuthState.initial() = _Initial;
  const factory AuthState.loading() = _Loading;
  const factory AuthState.authenticated(UserEntity user) = _Authenticated;
  const factory AuthState.unauthenticated() = _Unauthenticated;
  const factory AuthState.error(String message) = _Error;

  const AuthState._();

  /// Get error message if in error state
  String? get errorMessage => maybeWhen(
        error: (message) => message,
        orElse: () => null,
      );
}

class AuthNotifier extends StateNotifier<AuthState> {
  final LoginUseCase _loginUseCase;
  final LogoutUseCase _logoutUseCase;
  final ChangePasswordUseCase _changePasswordUseCase;

  AuthNotifier({
    required LoginUseCase loginUseCase,
    required LogoutUseCase logoutUseCase,
    required ChangePasswordUseCase changePasswordUseCase,
  })  : _loginUseCase = loginUseCase,
        _logoutUseCase = logoutUseCase,
        _changePasswordUseCase = changePasswordUseCase,
        super(const AuthState.initial());

  Future<void> login({required String email, required String password}) async {
    state = const AuthState.loading();

    final result = await _loginUseCase(email: email, password: password);

    result.fold(
      (failure) => state = AuthState.error(failure.message),
      (user) => state = AuthState.authenticated(user),
    );
  }

  Future<void> logout() async {
    final result = await _logoutUseCase();

    result.fold(
      (failure) => state = AuthState.error(failure.message),
      (_) => state = const AuthState.unauthenticated(),
    );
  }

  Future<bool> changePassword({
    required String currentPassword,
    required String newPassword,
  }) async {
    state = const AuthState.loading();

    final result = await _changePasswordUseCase(
      ChangePasswordParams(
        currentPassword: currentPassword,
        newPassword: newPassword,
      ),
    );

    return result.fold(
      (failure) {
        state = AuthState.error(failure.message);
        return false;
      },
      (_) {
        // Return to authenticated state after successful password change
        state.maybeWhen(
          authenticated: (user) => state = AuthState.authenticated(user),
          orElse: () => state = const AuthState.unauthenticated(),
        );
        return true;
      },
    );
  }
}
