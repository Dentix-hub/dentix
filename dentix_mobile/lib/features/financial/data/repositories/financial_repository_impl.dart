import 'package:dartz/dartz.dart';
import 'package:dio/dio.dart';

import '../../../../core/error/failures.dart';
import '../../../../core/network/network_exceptions.dart';
import '../../domain/entities/financial_transaction_entity.dart';
import '../../domain/repositories/financial_repository.dart';
import '../datasources/financial_remote.dart';

/// Implementation of FinancialRepository
class FinancialRepositoryImpl implements FinancialRepository {
  final FinancialRemoteDataSource _remoteDataSource;

  FinancialRepositoryImpl(this._remoteDataSource);

  @override
  Future<Either<Failure, FinancialOverviewEntity>> getFinancialOverview({
    required int page,
    required int limit,
    String? month,
  }) async {
    try {
      final result = await _remoteDataSource.getFinancialOverview(
        page: page,
        limit: limit,
        month: month,
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
  Future<Either<Failure, FinancialTransactionEntity>> recordPayment({
    required int patientId,
    required double amount,
    required String date,
    String? description,
    int? appointmentId,
    int? treatmentId,
  }) async {
    try {
      final result = await _remoteDataSource.recordPayment(
        patientId: patientId,
        amount: amount,
        date: date,
        description: description,
        appointmentId: appointmentId,
        treatmentId: treatmentId,
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
}
