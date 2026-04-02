// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'treatment_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$TreatmentModelImpl _$$TreatmentModelImplFromJson(Map<String, dynamic> json) =>
    _$TreatmentModelImpl(
      id: (json['id'] as num).toInt(),
      patientId: (json['patient_id'] as num).toInt(),
      appointmentId: (json['appointment_id'] as num?)?.toInt(),
      procedureType: json['procedure_type'] as String,
      description: json['description'] as String?,
      cost: (json['cost'] as num).toDouble(),
      status: json['status'] as String,
      treatmentDate: json['treatment_date'] as String,
      createdAt: json['created_at'] as String?,
      updatedAt: json['updated_at'] as String?,
    );

Map<String, dynamic> _$$TreatmentModelImplToJson(
        _$TreatmentModelImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'patient_id': instance.patientId,
      'appointment_id': instance.appointmentId,
      'procedure_type': instance.procedureType,
      'description': instance.description,
      'cost': instance.cost,
      'status': instance.status,
      'treatment_date': instance.treatmentDate,
      'created_at': instance.createdAt,
      'updated_at': instance.updatedAt,
    };

_$TreatmentListResponseImpl _$$TreatmentListResponseImplFromJson(
        Map<String, dynamic> json) =>
    _$TreatmentListResponseImpl(
      items: (json['items'] as List<dynamic>)
          .map((e) => TreatmentModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      total: (json['total'] as num).toInt(),
      currentPage: (json['page'] as num).toInt(),
      totalPages: (json['pages'] as num).toInt(),
    );

Map<String, dynamic> _$$TreatmentListResponseImplToJson(
        _$TreatmentListResponseImpl instance) =>
    <String, dynamic>{
      'items': instance.items,
      'total': instance.total,
      'page': instance.currentPage,
      'pages': instance.totalPages,
    };
