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

  @override
  Future<TokenModel> login({
    required String email,
    required String password,
  }) async {
    try {
      final response = await dio.post(
        ApiEndpoints.login,
        data: {
          'username': email,
          'password': password,
        },
        options: Options(
          contentType: Headers.formUrlEncodedContentType,
        ),
      );

      if (response.statusCode == 200) {
        return TokenModel.fromJson(_parseResponse(response.data));
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
        errorMessage = data['detail'] as String? ??
            (data['error'] is Map ? data['error']['message'] as String? : null) ??
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
        return UserModel.fromJson(_parseResponse(response.data));
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
      final response = await dio.post(
        ApiEndpoints.changePassword,
        data: {
          'current_password': currentPassword,
          'new_password': newPassword,
        },
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
