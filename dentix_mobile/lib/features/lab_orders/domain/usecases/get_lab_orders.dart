import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../../../../core/usecases/usecase.dart';
import '../entities/lab_order_entity.dart';
import '../repositories/lab_order_repository.dart';

/// Use case to get lab orders with pagination
class GetLabOrdersUseCase
    implements UseCase<LabOrderListEntity, GetLabOrdersParams> {
  final LabOrderRepository repository;

  GetLabOrdersUseCase(this.repository);

  @override
  Future<Either<Failure, LabOrderListEntity>> call(
    GetLabOrdersParams params,
  ) async {
    return await repository.getLabOrders(
      page: params.page,
      limit: params.limit,
      patientId: params.patientId,
      status: params.status,
    );
  }
}

/// Parameters for GetLabOrdersUseCase
class GetLabOrdersParams {
  final int page;
  final int limit;
  final int? patientId;
  final LabOrderStatus? status;

  GetLabOrdersParams({
    required this.page,
    required this.limit,
    this.patientId,
    this.status,
  });
}
