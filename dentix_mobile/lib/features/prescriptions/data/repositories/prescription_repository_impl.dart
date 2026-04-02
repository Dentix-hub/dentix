import 'package:dartz/dartz.dart';
import 'package:dio/dio.dart';

import '../../../../core/error/failures.dart';
import '../../../../core/network/network_exceptions.dart';
import '../../domain/entities/prescription_entity.dart';
import '../../domain/repositories/prescription_repository.dart';
import '../datasources/prescription_remote.dart';

/// Implementation of PrescriptionRepository
class PrescriptionRepositoryImpl implements PrescriptionRepository {
  final PrescriptionRemoteDataSource _remoteDataSource;

  PrescriptionRepositoryImpl(this._remoteDataSource);

  @override
  Future<Either<Failure, PrescriptionListEntity>> getPrescriptions({
    required int page,
    required int limit,
    int? patientId,
  }) async {
    try {
      final result = await _remoteDataSource.getPrescriptions(
        page: page,
        limit: limit,
        patientId: patientId,
      );
      return Right(result.toEntity());
    } on DioException catch (e) {
      return Left(ServerFailure(
        message: NetworkExceptions.getErrorMessage(
          NetworkExceptions.getDioException(e),
        ),
      ));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, PrescriptionEntity>> getPrescriptionById(int id) async {
    try {
      final result = await _remoteDataSource.getPrescriptionById(id);
      return Right(result.toEntity());
    } on DioException catch (e) {
      return Left(ServerFailure(
        message: NetworkExceptions.getErrorMessage(
          NetworkExceptions.getDioException(e),
        ),
      ));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, PrescriptionEntity>> createPrescription({
    required int patientId,
    required List<Map<String, dynamic>> medications,
    String? notes,
  }) async {
    try {
      final result = await _remoteDataSource.createPrescription(
        patientId: patientId,
        medications: medications,
        notes: notes,
      );
      return Right(result.toEntity());
    } on DioException catch (e) {
      return Left(ServerFailure(
        message: NetworkExceptions.getErrorMessage(
          NetworkExceptions.getDioException(e),
        ),
      ));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, PrescriptionEntity>> updatePrescription({
    required int id,
    required List<Map<String, dynamic>> medications,
    String? notes,
  }) async {
    try {
      final result = await _remoteDataSource.updatePrescription(
        id: id,
        medications: medications,
        notes: notes,
      );
      return Right(result.toEntity());
    } on DioException catch (e) {
      return Left(ServerFailure(
        message: NetworkExceptions.getErrorMessage(
          NetworkExceptions.getDioException(e),
        ),
      ));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> deletePrescription(int id) async {
    try {
      await _remoteDataSource.deletePrescription(id);
      return const Right(null);
    } on DioException catch (e) {
      return Left(ServerFailure(
        message: NetworkExceptions.getErrorMessage(
          NetworkExceptions.getDioException(e),
        ),
      ));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }
}
