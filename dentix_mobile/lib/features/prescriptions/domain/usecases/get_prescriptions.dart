import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../../../../core/usecases/usecase.dart';
import '../entities/prescription_entity.dart';
import '../repositories/prescription_repository.dart';

/// Use case to get prescriptions with pagination
class GetPrescriptionsUseCase
    implements UseCase<PrescriptionListEntity, GetPrescriptionsParams> {
  final PrescriptionRepository repository;

  GetPrescriptionsUseCase(this.repository);

  @override
  Future<Either<Failure, PrescriptionListEntity>> call(
    GetPrescriptionsParams params,
  ) async {
    return await repository.getPrescriptions(
      page: params.page,
      limit: params.limit,
      patientId: params.patientId,
    );
  }
}

/// Parameters for GetPrescriptionsUseCase
class GetPrescriptionsParams {
  final int page;
  final int limit;
  final int? patientId;

  GetPrescriptionsParams({
    required this.page,
    required this.limit,
    this.patientId,
  });
}
