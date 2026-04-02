import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../entities/treatment_entity.dart';
import '../repositories/treatment_repository.dart';

class GetTreatmentsByPatientIdUseCase {
  final TreatmentRepository repository;

  GetTreatmentsByPatientIdUseCase({required this.repository});

  Future<Either<Failure, TreatmentListEntity>> call({
    required int patientId,
    required int page,
    required int limit,
  }) async {
    return await repository.getTreatmentsByPatientId(
      patientId: patientId,
      page: page,
      limit: limit,
    );
  }
}

class GetTreatmentByIdUseCase {
  final TreatmentRepository repository;

  GetTreatmentByIdUseCase({required this.repository});

  Future<Either<Failure, TreatmentEntity>> call(int id) async {
    return await repository.getTreatmentById(id);
  }
}
