import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../../../../core/usecases/usecase.dart';
import '../entities/prescription_entity.dart';
import '../repositories/prescription_repository.dart';

/// Use case to create a new prescription
class CreatePrescriptionUseCase
    implements UseCase<PrescriptionEntity, CreatePrescriptionParams> {
  final PrescriptionRepository repository;

  CreatePrescriptionUseCase(this.repository);

  @override
  Future<Either<Failure, PrescriptionEntity>> call(
    CreatePrescriptionParams params,
  ) async {
    return await repository.createPrescription(
      patientId: params.patientId,
      medications: params.medications,
      notes: params.notes,
    );
  }
}

/// Parameters for CreatePrescriptionUseCase
class CreatePrescriptionParams {
  final int patientId;
  final List<Map<String, dynamic>> medications;
  final String? notes;

  CreatePrescriptionParams({
    required this.patientId,
    required this.medications,
    this.notes,
  });
}
