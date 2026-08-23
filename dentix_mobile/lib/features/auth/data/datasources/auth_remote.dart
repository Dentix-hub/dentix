import 'dart:convert';

import 'package:dio/dio.dart';

import '../../../../core/constants/api_endpoints.dart';
import '../../../../core/error/exceptions.dart';
import '../models/token_model.dart';
import '../models/user_model.dart';

abstract class AuthRemoteDataSource {
  Future<TokenModel> login({required String email, required String password});
  Future<TokenModel> refreshToken({required String refreshToken});
  Future<UserModel> getCurrentUser();
  Future<void> changePassword({
    required String currentPassword,
    required String newPassword,
  });
}

class AuthRemoteDataSourceImpl implements AuthRemoteDataSource {
  final Dio dio;

  AuthRemoteDataSourceImpl({required this.dio});

  /// Safely parse response data that may be a String or Map
  Map<String, dynamic> _parseResponse(dynamic data) {
    if (data is Map<String, dynamic>) return data;
    if (data is String) return jsonDecode(data) as Map<String, dynamic>;
    throw ServerException(message: 'Unexpected response format', code: 500);
  }

  /// StandardResponse envelopes ({success, data}) unwrap to their payload;
  /// raw payloads pass through untouched.
  dynamic _unwrap(dynamic data) {
    final parsed = _parseResponse(data);
    if (parsed.containsKey('success') && parsed.containsKey('data')) {
      final inner = parsed['data'];
      if (inner is Map<String, dynamic>) return inner;
    }
    return parsed;
  }

  @override
  Future<TokenModel> login({
    required String email,
    required String password,
  }) async {
    try {
      final response = await dio.post(
        ApiEndpoints.login,
        data: {'username': email, 'password': password},
        options: Options(contentType: Headers.formUrlEncodedContentType),
      );

      if (response.statusCode == 200) {
        final body = _parseResponse(response.data);
        // 2FA pending: the backend intentionally withholds a refresh token
        // until the OTP is verified; TokenModel requires the field, so an
        // empty placeholder keeps the pending state representable.
        final is2faPending = body['user_status'] == '2fa_required';
        return TokenModel.fromJson({
          ...body,
          'refresh_token': body['refresh_token'] ?? (is2faPending ? '' : null),
          'role': body['role'] ?? '',
          'username': body['username'] ?? email,
        });
      } else {
        throw ServerException(
          message: response.data?['message'] ?? 'Login failed',
          code: response.statusCode,
        );
      }
    } on DioException catch (e) {
      final data = e.response?.data;
      String errorMessage = 'Network error during login';
      if (data is Map<String, dynamic>) {
        // Backend returns {error: {message: "..."}} or {detail: "..."}
        errorMessage =
            data['detail'] as String? ??
            (data['error'] is Map
                ? data['error']['message'] as String?
                : null) ??
            data['message'] as String? ??
            errorMessage;
      }
      throw ServerException(
        message: errorMessage,
        code: e.response?.statusCode,
      );
    }
  }

  @override
  Future<TokenModel> refreshToken({required String refreshToken}) async {
    try {
      final response = await dio.post(
        ApiEndpoints.refresh,
        data: {'refresh_token': refreshToken},
      );

      if (response.statusCode == 200) {
        return TokenModel.fromJson(_parseResponse(response.data));
      } else {
        throw AuthException(message: 'Token refresh failed');
      }
    } on DioException catch (e) {
      throw AuthException(
        message: e.response?.data?['message'] ?? 'Failed to refresh token',
      );
    }
  }

  @override
  Future<UserModel> getCurrentUser() async {
    try {
      final response = await dio.get(ApiEndpoints.me);

      if (response.statusCode == 200) {
        // /users/me answers in a StandardResponse envelope.
        return UserModel.fromJson(_parseResponse(_unwrap(response.data)));
      } else {
        throw ServerException(
          message: response.data?['message'] ?? 'Failed to get user',
          code: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw ServerException(
        message: e.response?.data?['message'] ?? 'Failed to get current user',
        code: e.response?.statusCode,
      );
    }
  }

  @override
  Future<void> changePassword({
    required String currentPassword,
    required String newPassword,
  }) async {
    try {
      // Canonical contract: PUT /users/me with UserUpdate.password (the web
      // app uses the same endpoint). currentPassword is kept in the API for
      // UX confirmation but is not part of the server contract.
      final response = await dio.put(
        ApiEndpoints.changePassword,
        data: {'password': newPassword},
      );

      if (response.statusCode != 200) {
        throw ServerException(
          message: response.data?['message'] ?? 'Failed to change password',
          code: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw ServerException(
        message: e.response?.data?['message'] ?? 'Failed to change password',
        code: e.response?.statusCode,
      );
    }
  }
}
