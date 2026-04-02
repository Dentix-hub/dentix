class ServerException implements Exception {
  final String message;
  final int? code;

  const ServerException({required this.message, this.code});

  @override
  String toString() => 'ServerException: $message (code: $code)';
}

class CacheException implements Exception {
  final String message;

  const CacheException({required this.message});

  @override
  String toString() => 'CacheException: $message';
}

class NetworkException implements Exception {
  final String message;

  const NetworkException({required this.message});

  @override
  String toString() => 'NetworkException: $message';
}

class AuthException implements Exception {
  final String message;

  const AuthException({required this.message});

  @override
  String toString() => 'AuthException: $message';
}

class ValidationException implements Exception {
  final String message;

  const ValidationException({required this.message});

  @override
  String toString() => 'ValidationException: $message';
}
