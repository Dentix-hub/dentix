import 'dart:io';

import 'package:dio/dio.dart';

/// Custom exception types for network errors
abstract class NetworkExceptions {
  const NetworkExceptions();

  /// Convert a DioException to a specific NetworkException type
  static NetworkExceptions getDioException(DioException error) {
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return const RequestTimeout();
      case DioExceptionType.badResponse:
        return _handleHttpError(error.response?.statusCode);
      case DioExceptionType.connectionError:
        return const NoInternetConnection();
      case DioExceptionType.cancel:
        return const RequestCancelled();
      default:
        return const UnexpectedError();
    }
  }

  /// Handle HTTP error codes
  static NetworkExceptions _handleHttpError(int? statusCode) {
    switch (statusCode) {
      case 400:
        return const BadRequest();
      case 401:
        return const Unauthorized();
      case 403:
        return const Forbidden();
      case 404:
        return const NotFound();
      case 409:
        return const Conflict();
      case 422:
        return const UnprocessableEntity();
      case 500:
        return const InternalServerError();
      case 502:
        return const BadGateway();
      case 503:
        return const ServiceUnavailable();
      default:
        return const UnexpectedError();
    }
  }

  /// Get a user-friendly error message
  static String getErrorMessage(NetworkExceptions exception) {
    return exception.when(
      requestTimeout: () => 'Connection timed out. Please try again.',
      noInternetConnection: () =>
          'No internet connection. Please check your network.',
      badRequest: () => 'Invalid request. Please check your input.',
      unauthorized: () => 'Session expired. Please log in again.',
      forbidden: () => 'You do not have permission to perform this action.',
      notFound: () => 'The requested resource was not found.',
      conflict: () => 'A conflict occurred. Please try again.',
      unprocessableEntity: () =>
          'Unable to process your request. Please check your input.',
      internalServerError: () =>
          'Server error. Please try again later.',
      badGateway: () =>
          'Gateway error. Please try again later.',
      serviceUnavailable: () =>
          'Service temporarily unavailable. Please try again later.',
      requestCancelled: () => 'Request was cancelled.',
      unexpectedError: () =>
          'An unexpected error occurred. Please try again.',
    );
  }

  /// Pattern matching for all exception types
  T when<T>({
    required T Function() requestTimeout,
    required T Function() noInternetConnection,
    required T Function() badRequest,
    required T Function() unauthorized,
    required T Function() forbidden,
    required T Function() notFound,
    required T Function() conflict,
    required T Function() unprocessableEntity,
    required T Function() internalServerError,
    required T Function() badGateway,
    required T Function() serviceUnavailable,
    required T Function() requestCancelled,
    required T Function() unexpectedError,
  }) {
    if (this is RequestTimeout) return requestTimeout();
    if (this is NoInternetConnection) return noInternetConnection();
    if (this is BadRequest) return badRequest();
    if (this is Unauthorized) return unauthorized();
    if (this is Forbidden) return forbidden();
    if (this is NotFound) return notFound();
    if (this is Conflict) return conflict();
    if (this is UnprocessableEntity) return unprocessableEntity();
    if (this is InternalServerError) return internalServerError();
    if (this is BadGateway) return badGateway();
    if (this is ServiceUnavailable) return serviceUnavailable();
    if (this is RequestCancelled) return requestCancelled();
    return unexpectedError();
  }
}

/// Specific exception classes
class RequestTimeout extends NetworkExceptions {
  const RequestTimeout();
}

class NoInternetConnection extends NetworkExceptions {
  const NoInternetConnection();
}

class BadRequest extends NetworkExceptions {
  const BadRequest();
}

class Unauthorized extends NetworkExceptions {
  const Unauthorized();
}

class Forbidden extends NetworkExceptions {
  const Forbidden();
}

class NotFound extends NetworkExceptions {
  const NotFound();
}

class Conflict extends NetworkExceptions {
  const Conflict();
}

class UnprocessableEntity extends NetworkExceptions {
  const UnprocessableEntity();
}

class InternalServerError extends NetworkExceptions {
  const InternalServerError();
}

class BadGateway extends NetworkExceptions {
  const BadGateway();
}

class ServiceUnavailable extends NetworkExceptions {
  const ServiceUnavailable();
}

class RequestCancelled extends NetworkExceptions {
  const RequestCancelled();
}

class UnexpectedError extends NetworkExceptions {
  const UnexpectedError();
}
