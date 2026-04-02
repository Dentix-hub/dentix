import 'package:equatable/equatable.dart';

class UserEntity extends Equatable {
  final String id;
  final String username;
  final String email;
  final String role;
  final String? tenantId;
  final bool is2faEnabled;

  const UserEntity({
    required this.id,
    required this.username,
    this.email = '',
    this.role = 'user',
    this.tenantId,
    this.is2faEnabled = false,
  });

  @override
  List<Object?> get props => [
        id,
        username,
        email,
        role,
        tenantId,
        is2faEnabled,
      ];
}

class TokenEntity extends Equatable {
  final String accessToken;
  final String refreshToken;
  final String role;
  final String username;

  const TokenEntity({
    required this.accessToken,
    required this.refreshToken,
    required this.role,
    required this.username,
  });

  @override
  List<Object?> get props => [
        accessToken,
        refreshToken,
        role,
        username,
      ];
}
