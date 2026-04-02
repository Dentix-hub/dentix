import 'package:freezed_annotation/freezed_annotation.dart';

part 'lab_order_entity.freezed.dart';

/// Lab order status enum
enum LabOrderStatus {
  pending,
  inProgress,
  completed,
  cancelled,
}

/// Lab order entity representing a lab work order
@freezed
class LabOrderEntity with _$LabOrderEntity {
  const factory LabOrderEntity({
    required int id,
    required int patientId,
    String? patientName,
    required int dentistId,
    String? dentistName,
    required String labName,
    required String orderDate,
    required String dueDate,
    required List<LabWorkItemEntity> items,
    String? notes,
    required LabOrderStatus status,
    String? receivedDate,
    double? totalCost,
    String? createdAt,
    String? updatedAt,
  }) = _LabOrderEntity;

  const LabOrderEntity._();

  /// Check if order is pending
  bool get isPending => status == LabOrderStatus.pending;

  /// Check if order is in progress
  bool get isInProgress => status == LabOrderStatus.inProgress;

  /// Check if order is completed
  bool get isCompleted => status == LabOrderStatus.completed;

  /// Check if order is overdue
  bool get isOverdue {
    if (isCompleted || receivedDate != null) return false;
    final due = DateTime.tryParse(dueDate);
    if (due == null) return false;
    return due.isBefore(DateTime.now());
  }
}

/// Individual lab work item within an order
@freezed
class LabWorkItemEntity with _$LabWorkItemEntity {
  const factory LabWorkItemEntity({
    required int id,
    required String workType,
    String? description,
    required int quantity,
    String? shade,
    String? material,
  }) = _LabWorkItemEntity;

  const LabWorkItemEntity._();
}

/// Paginated list of lab orders
@freezed
class LabOrderListEntity with _$LabOrderListEntity {
  const factory LabOrderListEntity({
    required List<LabOrderEntity> items,
    required int currentPage,
    required int totalPages,
    required int totalItems,
  }) = _LabOrderListEntity;

  const LabOrderListEntity._();
}
