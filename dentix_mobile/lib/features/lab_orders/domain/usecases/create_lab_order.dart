import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../../../../core/usecases/usecase.dart';
import '../entities/lab_order_entity.dart';
import '../repositories/lab_order_repository.dart';

/// Use case to create a new lab order
class CreateLabOrderUseCase
    implements UseCase<LabOrderEntity, CreateLabOrderParams> {
  final LabOrderRepository repository;

  CreateLabOrderUseCase(this.repository);

  @override
  Future<Either<Failure, LabOrderEntity>> call(CreateLabOrderParams params) async {
    return await repository.createLabOrder(
      patientId: params.patientId,
      labName: params.labName,
      dueDate: params.dueDate,
      items: params.items,
      notes: params.notes,
    );
  }
}

class CreateLabOrderParams {
  final int patientId;
  final String labName;
  final String dueDate;
  final List<Map<String, dynamic>> items;
  final String? notes;

  CreateLabOrderParams({
    required this.patientId,
    required this.labName,
    required this.dueDate,
    required this.items,
    this.notes,
  });
}
