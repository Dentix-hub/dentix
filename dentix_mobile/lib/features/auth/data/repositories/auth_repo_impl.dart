import 'package:dartz/dartz.dart';

import '../../../../core/error/exceptions.dart';
import '../../../../core/error/failures.dart';
import '../../../../core/network/auth_interceptor.dart';
import '../../data/datasources/auth_remote.dart';
import '../../domain/entities/user_entity.dart';
import '../../domain/repositories/auth_repository.dart';

class AuthRepositoryImpl implements AuthRepository {
  final AuthRemoteDataSource remoteDataSource;
  final AuthInterceptor authInterceptor;

  AuthRepositoryImpl({
    required this.remoteDataSource,
    required this.authInterceptor,
  });

  @override
  Future<Either<Failure, UserEntity>> login({
    required String email,
    required String password,
  }) async {
    try {
      final tokenModel = await remoteDataSource.login(
        email: email,
        password: password,
      );

      // Save tokens
      await authInterceptor.saveTokens(
        accessToken: tokenModel.accessToken,
        refreshToken: tokenModel.refreshToken,
      );

      // Get user details
      final user = await remoteDataSource.getCurrentUser();

      return Right(UserEntity(
        id: user.id,
        username: user.username,
        email: user.email,
        role: user.role,
        tenantId: user.tenantId,
        is2faEnabled: user.is2faEnabled,
      ));
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message, code: e.code));
    } on AuthException catch (e) {
      return Left(AuthFailure(message: e.message));
    } catch (e) {
      return Left(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> logout() async {
    try {
      await authInterceptor.clearTokens();
      return const Right(null);
    } catch (e) {
      return Left(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, bool>> isLoggedIn() async {
    try {
      final loggedIn = await authInterceptor.isLoggedIn();
      return Right(loggedIn);
    } catch (e) {
      return Left(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, UserEntity>> getCurrentUser() async {
    try {
      final user = await remoteDataSource.getCurrentUser();

      return Right(UserEntity(
        id: user.id,
        username: user.username,
        email: user.email,
        role: user.role,
        tenantId: user.tenantId,
        is2faEnabled: user.is2faEnabled,
      ));
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message, code: e.code));
    } catch (e) {
      return Left(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> changePassword({
    required String currentPassword,
    required String newPassword,
  }) async {
    try {
      await remoteDataSource.changePassword(
        currentPassword: currentPassword,
        newPassword: newPassword,
      );
      return const Right(null);
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message, code: e.code));
    } catch (e) {
      return Left(UnknownFailure(message: e.toString()));
    }
  }
}
