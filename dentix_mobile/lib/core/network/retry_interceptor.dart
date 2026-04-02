import 'dart:io';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import 'dio_client.dart';

class RetryInterceptor extends Interceptor {
  final int maxRetries;
  final Duration retryDelay;

  RetryInterceptor({
    this.maxRetries = 3,
    this.retryDelay = const Duration(seconds: 1),
  });

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    if (_shouldRetry(err) && err.requestOptions.extra['retryCount'] != maxRetries) {
      final retryCount = (err.requestOptions.extra['retryCount'] ?? 0) as int;
      
      if (retryCount < maxRetries) {
        debugPrint('Retrying request (${retryCount + 1}/$maxRetries)...');
        
        await Future.delayed(retryDelay * (retryCount + 1));
        
        err.requestOptions.extra['retryCount'] = retryCount + 1;
        
        try {
          final response = await DioClient.dio.fetch(err.requestOptions);
          return handler.resolve(response);
        } on DioException catch (e) {
          return handler.next(e);
        }
      }
    }
    
    return handler.next(err);
  }

  bool _shouldRetry(DioException error) {
    return error.type == DioExceptionType.connectionTimeout ||
        error.type == DioExceptionType.sendTimeout ||
        error.type == DioExceptionType.receiveTimeout ||
        error.type == DioExceptionType.connectionError ||
        (error.error is SocketException);
  }
}
