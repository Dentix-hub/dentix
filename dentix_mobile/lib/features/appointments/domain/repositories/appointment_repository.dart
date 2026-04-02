import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../entities/appointment_entity.dart';

abstract class AppointmentRepository {
  Future<Either<Failure, AppointmentListEntity>> getAppointments({
    required int page,
    required int limit,
    String? date,
    String? startDate,
    String? endDate,
    int? patientId,
  });
  
  Future<Either<Failure, AppointmentEntity>> getAppointmentById(int id);
  
  Future<Either<Failure, AppointmentEntity>> createAppointment({
    required int patientId,
    required int dentistId,
    required String appointmentDate,
    required String startTime,
    String? endTime,
    String? notes,
    String? procedureType,
  });
  
  Future<Either<Failure, AppointmentEntity>> updateAppointment({
    required int id,
    required int patientId,
    required int dentistId,
    required String appointmentDate,
    required String startTime,
    String? endTime,
    String? notes,
    String? procedureType,
  });
  
  Future<Either<Failure, void>> cancelAppointment(int id);
  
  Future<Either<Failure, void>> completeAppointment(int id);
}
