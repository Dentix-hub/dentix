// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'prescription_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$PrescribedMedicationModelImpl _$$PrescribedMedicationModelImplFromJson(
        Map<String, dynamic> json) =>
    _$PrescribedMedicationModelImpl(
      id: (json['id'] as num).toInt(),
      medicationId: (json['medication_id'] as num).toInt(),
      medicationName: json['medication_name'] as String?,
      dosage: json['dosage'] as String?,
      frequency: json['frequency'] as String?,
      duration: json['duration'] as String?,
      instructions: json['instructions'] as String?,
    );

Map<String, dynamic> _$$PrescribedMedicationModelImplToJson(
        _$PrescribedMedicationModelImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'medication_id': instance.medicationId,
      'medication_name': instance.medicationName,
      'dosage': instance.dosage,
      'frequency': instance.frequency,
      'duration': instance.duration,
      'instructions': instance.instructions,
    };

_$PrescriptionModelImpl _$$PrescriptionModelImplFromJson(
        Map<String, dynamic> json) =>
    _$PrescriptionModelImpl(
      id: (json['id'] as num).toInt(),
      patientId: (json['patient_id'] as num).toInt(),
      patientName: json['patient_name'] as String?,
      dentistId: (json['dentist_id'] as num).toInt(),
      dentistName: json['dentist_name'] as String?,
      prescriptionDate: json['prescription_date'] as String,
      medications: (json['medications'] as List<dynamic>)
          .map((e) =>
              PrescribedMedicationModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      notes: json['notes'] as String?,
      status: json['status'] as String?,
      createdAt: json['created_at'] as String?,
      updatedAt: json['updated_at'] as String?,
    );

Map<String, dynamic> _$$PrescriptionModelImplToJson(
        _$PrescriptionModelImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'patient_id': instance.patientId,
      'patient_name': instance.patientName,
      'dentist_id': instance.dentistId,
      'dentist_name': instance.dentistName,
      'prescription_date': instance.prescriptionDate,
      'medications': instance.medications,
      'notes': instance.notes,
      'status': instance.status,
      'created_at': instance.createdAt,
      'updated_at': instance.updatedAt,
    };

_$PrescriptionListResponseModelImpl
    _$$PrescriptionListResponseModelImplFromJson(Map<String, dynamic> json) =>
        _$PrescriptionListResponseModelImpl(
          items: (json['items'] as List<dynamic>)
              .map((e) => PrescriptionModel.fromJson(e as Map<String, dynamic>))
              .toList(),
          currentPage: (json['current_page'] as num).toInt(),
          totalPages: (json['total_pages'] as num).toInt(),
          totalItems: (json['total_items'] as num).toInt(),
        );

Map<String, dynamic> _$$PrescriptionListResponseModelImplToJson(
        _$PrescriptionListResponseModelImpl instance) =>
    <String, dynamic>{
      'items': instance.items,
      'current_page': instance.currentPage,
      'total_pages': instance.totalPages,
      'total_items': instance.totalItems,
    };

_$CreatePrescriptionRequestModelImpl
    _$$CreatePrescriptionRequestModelImplFromJson(Map<String, dynamic> json) =>
        _$CreatePrescriptionRequestModelImpl(
          patientId: (json['patient_id'] as num).toInt(),
          medications: (json['medications'] as List<dynamic>)
              .map((e) => e as Map<String, dynamic>)
              .toList(),
          notes: json['notes'] as String?,
        );

Map<String, dynamic> _$$CreatePrescriptionRequestModelImplToJson(
        _$CreatePrescriptionRequestModelImpl instance) =>
    <String, dynamic>{
      'patient_id': instance.patientId,
      'medications': instance.medications,
      'notes': instance.notes,
    };
