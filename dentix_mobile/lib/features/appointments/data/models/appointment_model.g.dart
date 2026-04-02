// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'appointment_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$AppointmentModelImpl _$$AppointmentModelImplFromJson(
        Map<String, dynamic> json) =>
    _$AppointmentModelImpl(
      id: (json['id'] as num).toInt(),
      patientId: (json['patient_id'] as num).toInt(),
      patientName: json['patient_name'] as String?,
      dentistId: (json['dentist_id'] as num).toInt(),
      dentistName: json['dentist_name'] as String?,
      appointmentDate: json['appointment_date'] as String,
      startTime: json['start_time'] as String,
      endTime: json['end_time'] as String?,
      status: json['status'] as String,
      notes: json['notes'] as String?,
      procedureType: json['procedure_type'] as String?,
      createdAt: json['created_at'] as String?,
      updatedAt: json['updated_at'] as String?,
    );

Map<String, dynamic> _$$AppointmentModelImplToJson(
        _$AppointmentModelImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'patient_id': instance.patientId,
      'patient_name': instance.patientName,
      'dentist_id': instance.dentistId,
      'dentist_name': instance.dentistName,
      'appointment_date': instance.appointmentDate,
      'start_time': instance.startTime,
      'end_time': instance.endTime,
      'status': instance.status,
      'notes': instance.notes,
      'procedure_type': instance.procedureType,
      'created_at': instance.createdAt,
      'updated_at': instance.updatedAt,
    };

_$AppointmentListResponseImpl _$$AppointmentListResponseImplFromJson(
        Map<String, dynamic> json) =>
    _$AppointmentListResponseImpl(
      items: (json['items'] as List<dynamic>)
          .map((e) => AppointmentModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      total: (json['total'] as num).toInt(),
      currentPage: (json['page'] as num).toInt(),
      totalPages: (json['pages'] as num).toInt(),
    );

Map<String, dynamic> _$$AppointmentListResponseImplToJson(
        _$AppointmentListResponseImpl instance) =>
    <String, dynamic>{
      'items': instance.items,
      'total': instance.total,
      'page': instance.currentPage,
      'pages': instance.totalPages,
    };

_$CreateAppointmentRequestImpl _$$CreateAppointmentRequestImplFromJson(
        Map<String, dynamic> json) =>
    _$CreateAppointmentRequestImpl(
      patientId: (json['patient_id'] as num).toInt(),
      dentistId: (json['dentist_id'] as num).toInt(),
      appointmentDate: json['appointment_date'] as String,
      startTime: json['start_time'] as String,
      endTime: json['end_time'] as String?,
      notes: json['notes'] as String?,
      procedureType: json['procedure_type'] as String?,
    );

Map<String, dynamic> _$$CreateAppointmentRequestImplToJson(
        _$CreateAppointmentRequestImpl instance) =>
    <String, dynamic>{
      'patient_id': instance.patientId,
      'dentist_id': instance.dentistId,
      'appointment_date': instance.appointmentDate,
      'start_time': instance.startTime,
      'end_time': instance.endTime,
      'notes': instance.notes,
      'procedure_type': instance.procedureType,
    };
