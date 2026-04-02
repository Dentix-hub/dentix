import 'package:freezed_annotation/freezed_annotation.dart';

import '../../domain/entities/lab_order_entity.dart';

part 'lab_order_model.freezed.dart';
part 'lab_order_model.g.dart';

@freezed
class LabWorkItemModel with _$LabWorkItemModel {
  const factory LabWorkItemModel({
    required int id,
    required String workType,
    String? description,
    required int quantity,
    String? shade,
    String? material,
  }) = _LabWorkItemModel;

  const LabWorkItemModel._();

  factory LabWorkItemModel.fromJson(Map<String, dynamic> json) =>
      _$LabWorkItemModelFromJson(json);

  LabWorkItemEntity toEntity() {
    return LabWorkItemEntity(
      id: id,
      workType: workType,
      description: description,
      quantity: quantity,
      shade: shade,
      material: material,
    );
  }
}

@freezed
class LabOrderModel with _$LabOrderModel {
  const factory LabOrderModel({
    required int id,
    @JsonKey(name: 'patient_id') required int patientId,
    @JsonKey(name: 'patient_name') String? patientName,
    @JsonKey(name: 'dentist_id') required int dentistId,
    @JsonKey(name: 'dentist_name') String? dentistName,
    @JsonKey(name: 'lab_name') required String labName,
    @JsonKey(name: 'order_date') required String orderDate,
    @JsonKey(name: 'due_date') required String dueDate,
    required List<LabWorkItemModel> items,
    String? notes,
    required String status,
    @JsonKey(name: 'received_date') String? receivedDate,
    @JsonKey(name: 'total_cost') double? totalCost,
    @JsonKey(name: 'created_at') String? createdAt,
    @JsonKey(name: 'updated_at') String? updatedAt,
  }) = _LabOrderModel;

  const LabOrderModel._();

  factory LabOrderModel.fromJson(Map<String, dynamic> json) =>
      _$LabOrderModelFromJson(json);

  LabOrderEntity toEntity() {
    return LabOrderEntity(
      id: id,
      patientId: patientId,
      patientName: patientName,
      dentistId: dentistId,
      dentistName: dentistName,
      labName: labName,
      orderDate: orderDate,
      dueDate: dueDate,
      items: items.map((e) => e.toEntity()).toList(),
      notes: notes,
      status: _parseStatus(status),
      receivedDate: receivedDate,
      totalCost: totalCost,
      createdAt: createdAt,
      updatedAt: updatedAt,
    );
  }

  static LabOrderStatus _parseStatus(String status) {
    return LabOrderStatus.values.firstWhere(
      (e) => e.name.toLowerCase() == status.toLowerCase().replaceAll('_', ''),
      orElse: () => LabOrderStatus.pending,
    );
  }
}

@freezed
class LabOrderListResponseModel with _$LabOrderListResponseModel {
  const factory LabOrderListResponseModel({
    required List<LabOrderModel> items,
    @JsonKey(name: 'current_page') required int currentPage,
    @JsonKey(name: 'total_pages') required int totalPages,
    @JsonKey(name: 'total_items') required int totalItems,
  }) = _LabOrderListResponseModel;

  const LabOrderListResponseModel._();

  factory LabOrderListResponseModel.fromJson(Map<String, dynamic> json) =>
      _$LabOrderListResponseModelFromJson(json);

  LabOrderListEntity toEntity() {
    return LabOrderListEntity(
      items: items.map((e) => e.toEntity()).toList(),
      currentPage: currentPage,
      totalPages: totalPages,
      totalItems: totalItems,
    );
  }
}

@freezed
class CreateLabOrderRequestModel with _$CreateLabOrderRequestModel {
  const factory CreateLabOrderRequestModel({
    @JsonKey(name: 'patient_id') required int patientId,
    @JsonKey(name: 'lab_name') required String labName,
    @JsonKey(name: 'due_date') required String dueDate,
    required List<Map<String, dynamic>> items,
    String? notes,
  }) = _CreateLabOrderRequestModel;

  const CreateLabOrderRequestModel._();

  factory CreateLabOrderRequestModel.fromJson(Map<String, dynamic> json) =>
      _$CreateLabOrderRequestModelFromJson(json);
}
