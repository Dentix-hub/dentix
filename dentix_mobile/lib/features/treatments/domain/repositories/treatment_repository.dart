import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../entities/treatment_entity.dart';

abstract class TreatmentRepository {
  Future<Either<Failure, TreatmentListEntity>> getTreatmentsByPatientId({
    required int patientId,
    required int page,
    required int limit,
  });
  
  Future<Either<Failure, TreatmentEntity>> getTreatmentById(int id);
}
