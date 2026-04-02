import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../constants/api_endpoints.dart';
import '../error/exceptions.dart';
import 'dio_client.dart';

class AuthInterceptor extends Interceptor {
  final FlutterSecureStorage _secureStorage;

  AuthInterceptor({FlutterSecureStorage? secureStorage})
      : _secureStorage = secureStorage ?? const FlutterSecureStorage();

  static const String _accessTokenKey = 'access_token';
  static const String _refreshTokenKey = 'refresh_token';

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    // Skip adding token for login and refresh endpoints
    if (options.path == ApiEndpoints.login ||
        options.path == ApiEndpoints.refresh) {
      return handler.next(options);
    }

    try {
      final token = await _secureStorage.read(key: _accessTokenKey);
      if (token != null) {
        options.headers['Authorization'] = 'Bearer $token';
      }
    } catch (e) {
      debugPrint('Error reading token: $e');
    }

    return handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    // Handle 401 - Token expired
    if (err.response?.statusCode == 401) {
      final refreshed = await _refreshToken();
      if (refreshed) {
        // Retry the original request
        final token = await _secureStorage.read(key: _accessTokenKey);
        final options = err.requestOptions;
        options.headers['Authorization'] = 'Bearer $token';
        
        try {
          final response = await DioClient.dio.fetch(options);
          return handler.resolve(response);
        } on DioException catch (e) {
          return handler.next(e);
        }
      } else {
        // Refresh failed, clear tokens
        await _clearTokens();
        return handler.reject(
          DioException(
            requestOptions: err.requestOptions,
            error: const AuthException(message: 'Session expired. Please login again.'),
          ),
        );
      }
    }

    return handler.next(err);
  }

  Future<bool> _refreshToken() async {
    try {
      final refreshToken = await _secureStorage.read(key: _refreshTokenKey);
      if (refreshToken == null) return false;

      final response = await DioClient.dio.post(
        ApiEndpoints.refresh,
        data: {'refresh_token': refreshToken},
        options: Options(
          contentType: Headers.formUrlEncodedContentType,
        ),
      );

      if (response.statusCode == 200) {
        final newAccessToken = response.data['access_token'] as String?;
        final newRefreshToken = response.data['refresh_token'] as String?;

        if (newAccessToken != null) {
          await _secureStorage.write(key: _accessTokenKey, value: newAccessToken);
        }
        if (newRefreshToken != null) {
          await _secureStorage.write(key: _refreshTokenKey, value: newRefreshToken);
        }

        return true;
      }
    } catch (e) {
      debugPrint('Token refresh failed: $e');
    }

    return false;
  }

  Future<void> _clearTokens() async {
    await _secureStorage.delete(key: _accessTokenKey);
    await _secureStorage.delete(key: _refreshTokenKey);
  }

  // Public methods for auth management
  Future<void> saveTokens({required String accessToken, required String refreshToken}) async {
    await _secureStorage.write(key: _accessTokenKey, value: accessToken);
    await _secureStorage.write(key: _refreshTokenKey, value: refreshToken);
  }

  Future<String?> getAccessToken() async {
    return await _secureStorage.read(key: _accessTokenKey);
  }

  Future<void> clearTokens() async {
    await _clearTokens();
  }

  Future<bool> isLoggedIn() async {
    final token = await _secureStorage.read(key: _accessTokenKey);
    return token != null;
  }
}
