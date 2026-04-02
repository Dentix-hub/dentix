import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../../../../core/error/exceptions.dart';
import '../../domain/entities/appointment_entity.dart';
import '../../domain/repositories/appointment_repository.dart';
import '../datasources/appointment_remote.dart';
import '../models/appointment_model.dart';

class AppointmentRepositoryImpl implements AppointmentRepository {
  final AppointmentRemoteDataSource remoteDataSource;

  AppointmentRepositoryImpl({required this.remoteDataSource});

  @override
  Future<Either<Failure, AppointmentListEntity>> getAppointments({
    required int page,
    required int limit,
    String? date,
    String? startDate,
    String? endDate,
    int? patientId,
  }) async {
    try {
      final result = await remoteDataSource.getAppointments(
        page: page,
        limit: limit,
        date: date,
        startDate: startDate,
        endDate: endDate,
        patientId: patientId,
      );
      return Right(_mapListResponseToEntity(result));
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } catch (e) {
      return Left(UnexpectedFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, AppointmentEntity>> getAppointmentById(int id) async {
    try {
      final result = await remoteDataSource.getAppointmentById(id);
      return Right(_mapModelToEntity(result));
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } catch (e) {
      return Left(UnexpectedFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, AppointmentEntity>> createAppointment({
    required int patientId,
    required int dentistId,
    required String appointmentDate,
    required String startTime,
    String? endTime,
    String? notes,
    String? procedureType,
  }) async {
    try {
      final request = CreateAppointmentRequest(
        patientId: patientId,
        dentistId: dentistId,
        appointmentDate: appointmentDate,
        startTime: startTime,
        endTime: endTime,
        notes: notes,
        procedureType: procedureType,
      );
      final result = await remoteDataSource.createAppointment(request);
      return Right(_mapModelToEntity(result));
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } catch (e) {
      return Left(UnexpectedFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, AppointmentEntity>> updateAppointment({
    required int id,
    required int patientId,
    required int dentistId,
    required String appointmentDate,
    required String startTime,
    String? endTime,
    String? notes,
    String? procedureType,
  }) async {
    try {
      final request = CreateAppointmentRequest(
        patientId: patientId,
        dentistId: dentistId,
        appointmentDate: appointmentDate,
        startTime: startTime,
        endTime: endTime,
        notes: notes,
        procedureType: procedureType,
      );
      final result = await remoteDataSource.updateAppointment(id, request);
      return Right(_mapModelToEntity(result));
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } catch (e) {
      return Left(UnexpectedFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> cancelAppointment(int id) async {
    try {
      await remoteDataSource.cancelAppointment(id);
      return const Right(null);
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } catch (e) {
      return Left(UnexpectedFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> completeAppointment(int id) async {
    try {
      await remoteDataSource.completeAppointment(id);
      return const Right(null);
    } on ServerException catch (e) {
      return Left(ServerFailure(message: e.message));
    } catch (e) {
      return Left(UnexpectedFailure(message: e.toString()));
    }
  }

  AppointmentListEntity _mapListResponseToEntity(AppointmentListResponse response) {
    return AppointmentListEntity(
      items: response.items.map(_mapModelToEntity).toList(),
      total: response.total,
      currentPage: response.currentPage,
      totalPages: response.totalPages,
    );
  }

  AppointmentEntity _mapModelToEntity(AppointmentModel model) {
    return AppointmentEntity(
      id: model.id,
      patientId: model.patientId,
      patientName: model.patientName,
      dentistId: model.dentistId,
      dentistName: model.dentistName,
      appointmentDate: model.appointmentDate,
      startTime: model.startTime,
      endTime: model.endTime,
      status: model.status,
      notes: model.notes,
      procedureType: model.procedureType,
      createdAt: model.createdAt,
      updatedAt: model.updatedAt,
    );
  }
}
