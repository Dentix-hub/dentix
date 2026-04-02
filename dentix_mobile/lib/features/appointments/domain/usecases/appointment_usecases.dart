import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../entities/appointment_entity.dart';
import '../repositories/appointment_repository.dart';

class GetAppointmentsUseCase {
  final AppointmentRepository repository;

  GetAppointmentsUseCase({required this.repository});

  Future<Either<Failure, AppointmentListEntity>> call({
    required int page,
    required int limit,
    String? date,
    String? startDate,
    String? endDate,
    int? patientId,
  }) async {
    return await repository.getAppointments(
      page: page,
      limit: limit,
      date: date,
      startDate: startDate,
      endDate: endDate,
      patientId: patientId,
    );
  }
}

class GetAppointmentByIdUseCase {
  final AppointmentRepository repository;

  GetAppointmentByIdUseCase({required this.repository});

  Future<Either<Failure, AppointmentEntity>> call(int id) async {
    return await repository.getAppointmentById(id);
  }
}

class CreateAppointmentUseCase {
  final AppointmentRepository repository;

  CreateAppointmentUseCase({required this.repository});

  Future<Either<Failure, AppointmentEntity>> call({
    required int patientId,
    required int dentistId,
    required String appointmentDate,
    required String startTime,
    String? endTime,
    String? notes,
    String? procedureType,
  }) async {
    return await repository.createAppointment(
      patientId: patientId,
      dentistId: dentistId,
      appointmentDate: appointmentDate,
      startTime: startTime,
      endTime: endTime,
      notes: notes,
      procedureType: procedureType,
    );
  }
}

class UpdateAppointmentUseCase {
  final AppointmentRepository repository;

  UpdateAppointmentUseCase({required this.repository});

  Future<Either<Failure, AppointmentEntity>> call({
    required int id,
    required int patientId,
    required int dentistId,
    required String appointmentDate,
    required String startTime,
    String? endTime,
    String? notes,
    String? procedureType,
  }) async {
    return await repository.updateAppointment(
      id: id,
      patientId: patientId,
      dentistId: dentistId,
      appointmentDate: appointmentDate,
      startTime: startTime,
      endTime: endTime,
      notes: notes,
      procedureType: procedureType,
    );
  }
}

class CancelAppointmentUseCase {
  final AppointmentRepository repository;

  CancelAppointmentUseCase({required this.repository});

  Future<Either<Failure, void>> call(int id) async {
    return await repository.cancelAppointment(id);
  }
}

class CompleteAppointmentUseCase {
  final AppointmentRepository repository;

  CompleteAppointmentUseCase({required this.repository});

  Future<Either<Failure, void>> call(int id) async {
    return await repository.completeAppointment(id);
  }
}
