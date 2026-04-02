import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

class DioClient {
  static Dio? _dio;

  static Dio get dio {
    _dio ??= _createDio();
    return _dio!;
  }

  static Dio _createDio() {
    final dio = Dio(
      BaseOptions(
        baseUrl: '', // Will be configured with actual backend URL
        connectTimeout: const Duration(seconds: 30),
        receiveTimeout: const Duration(seconds: 30),
        sendTimeout: const Duration(seconds: 30),
        responseType: ResponseType.json,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ),
    );

    // Auto-parse String responses to JSON (Flutter web workaround)
    dio.interceptors.add(
      InterceptorsWrapper(
        onResponse: (response, handler) {
          if (response.data is String && response.data != null) {
            try {
              response.data = jsonDecode(response.data as String);
            } catch (_) {
              // Not valid JSON, leave as-is
            }
          }
          handler.next(response);
        },
      ),
    );

    if (kDebugMode) {
      dio.interceptors.add(
        LogInterceptor(
          request: true,
          requestHeader: true,
          requestBody: true,
          responseHeader: true,
          responseBody: true,
          error: true,
          logPrint: (object) => debugPrint(object.toString()),
        ),
      );
    }

    return dio;
  }

  static void configureBaseUrl(String baseUrl) {
    dio.options.baseUrl = baseUrl;
  }

  static void addInterceptor(Interceptor interceptor) {
    dio.interceptors.add(interceptor);
  }

  static void clearInterceptors() {
    dio.interceptors.clear();
  }
}
