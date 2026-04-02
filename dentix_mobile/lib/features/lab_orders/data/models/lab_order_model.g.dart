// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'lab_order_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$LabWorkItemModelImpl _$$LabWorkItemModelImplFromJson(
        Map<String, dynamic> json) =>
    _$LabWorkItemModelImpl(
      id: (json['id'] as num).toInt(),
      workType: json['workType'] as String,
      description: json['description'] as String?,
      quantity: (json['quantity'] as num).toInt(),
      shade: json['shade'] as String?,
      material: json['material'] as String?,
    );

Map<String, dynamic> _$$LabWorkItemModelImplToJson(
        _$LabWorkItemModelImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'workType': instance.workType,
      'description': instance.description,
      'quantity': instance.quantity,
      'shade': instance.shade,
      'material': instance.material,
    };

_$LabOrderModelImpl _$$LabOrderModelImplFromJson(Map<String, dynamic> json) =>
    _$LabOrderModelImpl(
      id: (json['id'] as num).toInt(),
      patientId: (json['patient_id'] as num).toInt(),
      patientName: json['patient_name'] as String?,
      dentistId: (json['dentist_id'] as num).toInt(),
      dentistName: json['dentist_name'] as String?,
      labName: json['lab_name'] as String,
      orderDate: json['order_date'] as String,
      dueDate: json['due_date'] as String,
      items: (json['items'] as List<dynamic>)
          .map((e) => LabWorkItemModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      notes: json['notes'] as String?,
      status: json['status'] as String,
      receivedDate: json['received_date'] as String?,
      totalCost: (json['total_cost'] as num?)?.toDouble(),
      createdAt: json['created_at'] as String?,
      updatedAt: json['updated_at'] as String?,
    );

Map<String, dynamic> _$$LabOrderModelImplToJson(_$LabOrderModelImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'patient_id': instance.patientId,
      'patient_name': instance.patientName,
      'dentist_id': instance.dentistId,
      'dentist_name': instance.dentistName,
      'lab_name': instance.labName,
      'order_date': instance.orderDate,
      'due_date': instance.dueDate,
      'items': instance.items,
      'notes': instance.notes,
      'status': instance.status,
      'received_date': instance.receivedDate,
      'total_cost': instance.totalCost,
      'created_at': instance.createdAt,
      'updated_at': instance.updatedAt,
    };

_$LabOrderListResponseModelImpl _$$LabOrderListResponseModelImplFromJson(
        Map<String, dynamic> json) =>
    _$LabOrderListResponseModelImpl(
      items: (json['items'] as List<dynamic>)
          .map((e) => LabOrderModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      currentPage: (json['current_page'] as num).toInt(),
      totalPages: (json['total_pages'] as num).toInt(),
      totalItems: (json['total_items'] as num).toInt(),
    );

Map<String, dynamic> _$$LabOrderListResponseModelImplToJson(
        _$LabOrderListResponseModelImpl instance) =>
    <String, dynamic>{
      'items': instance.items,
      'current_page': instance.currentPage,
      'total_pages': instance.totalPages,
      'total_items': instance.totalItems,
    };

_$CreateLabOrderRequestModelImpl _$$CreateLabOrderRequestModelImplFromJson(
        Map<String, dynamic> json) =>
    _$CreateLabOrderRequestModelImpl(
      patientId: (json['patient_id'] as num).toInt(),
      labName: json['lab_name'] as String,
      dueDate: json['due_date'] as String,
      items: (json['items'] as List<dynamic>)
          .map((e) => e as Map<String, dynamic>)
          .toList(),
      notes: json['notes'] as String?,
    );

Map<String, dynamic> _$$CreateLabOrderRequestModelImplToJson(
        _$CreateLabOrderRequestModelImpl instance) =>
    <String, dynamic>{
      'patient_id': instance.patientId,
      'lab_name': instance.labName,
      'due_date': instance.dueDate,
      'items': instance.items,
      'notes': instance.notes,
    };
