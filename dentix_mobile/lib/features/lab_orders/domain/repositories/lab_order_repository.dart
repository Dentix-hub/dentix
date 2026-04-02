import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../entities/lab_order_entity.dart';

/// Repository interface for lab order operations
abstract class LabOrderRepository {
  /// Get lab orders list with pagination and optional filters
  ///
  /// [page] - Page number for pagination
  /// [limit] - Items per page
  /// [patientId] - Optional filter by patient
  /// [status] - Optional filter by status
  Future<Either<Failure, LabOrderListEntity>> getLabOrders({
    required int page,
    required int limit,
    int? patientId,
    LabOrderStatus? status,
  });

  /// Get a single lab order by ID
  Future<Either<Failure, LabOrderEntity>> getLabOrderById(int id);

  /// Create a new lab order
  Future<Either<Failure, LabOrderEntity>> createLabOrder({
    required int patientId,
    required String labName,
    required String dueDate,
    required List<Map<String, dynamic>> items,
    String? notes,
  });

  /// Update lab order status
  Future<Either<Failure, LabOrderEntity>> updateLabOrderStatus({
    required int id,
    required LabOrderStatus status,
    String? receivedDate,
  });

  /// Delete a lab order
  Future<Either<Failure, void>> deleteLabOrder(int id);
}
