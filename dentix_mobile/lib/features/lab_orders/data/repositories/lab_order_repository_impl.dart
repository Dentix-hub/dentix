import 'package:dartz/dartz.dart';
import 'package:dio/dio.dart';

import '../../../../core/error/failures.dart';
import '../../../../core/network/network_exceptions.dart';
import '../../domain/entities/lab_order_entity.dart';
import '../../domain/repositories/lab_order_repository.dart';
import '../datasources/lab_order_remote.dart';

class LabOrderRepositoryImpl implements LabOrderRepository {
  final LabOrderRemoteDataSource _remoteDataSource;

  LabOrderRepositoryImpl(this._remoteDataSource);

  @override
  Future<Either<Failure, LabOrderListEntity>> getLabOrders({
    required int page,
    required int limit,
    int? patientId,
    LabOrderStatus? status,
  }) async {
    try {
      final result = await _remoteDataSource.getLabOrders(
        page: page,
        limit: limit,
        patientId: patientId,
        status: status,
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
  Future<Either<Failure, LabOrderEntity>> getLabOrderById(int id) async {
    try {
      final result = await _remoteDataSource.getLabOrderById(id);
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
  Future<Either<Failure, LabOrderEntity>> createLabOrder({
    required int patientId,
    required String labName,
    required String dueDate,
    required List<Map<String, dynamic>> items,
    String? notes,
  }) async {
    try {
      final result = await _remoteDataSource.createLabOrder(
        patientId: patientId,
        labName: labName,
        dueDate: dueDate,
        items: items,
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
  Future<Either<Failure, LabOrderEntity>> updateLabOrderStatus({
    required int id,
    required LabOrderStatus status,
    String? receivedDate,
  }) async {
    try {
      final result = await _remoteDataSource.updateLabOrderStatus(
        id: id,
        status: status,
        receivedDate: receivedDate,
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
  Future<Either<Failure, void>> deleteLabOrder(int id) async {
    try {
      await _remoteDataSource.deleteLabOrder(id);
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
