// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'patient_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$PatientModelImpl _$$PatientModelImplFromJson(Map<String, dynamic> json) =>
    _$PatientModelImpl(
      id: (json['id'] as num).toInt(),
      fullName: json['full_name'] as String,
      phone: json['phone'] as String?,
      email: json['email'] as String?,
      dateOfBirth: json['date_of_birth'] as String?,
      gender: json['gender'] as String?,
      address: json['address'] as String?,
      medicalHistory: json['medical_history'] as String?,
      allergies: json['allergies'] as String?,
      createdAt: json['created_at'] as String?,
      updatedAt: json['updated_at'] as String?,
    );

Map<String, dynamic> _$$PatientModelImplToJson(_$PatientModelImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'full_name': instance.fullName,
      'phone': instance.phone,
      'email': instance.email,
      'date_of_birth': instance.dateOfBirth,
      'gender': instance.gender,
      'address': instance.address,
      'medical_history': instance.medicalHistory,
      'allergies': instance.allergies,
      'created_at': instance.createdAt,
      'updated_at': instance.updatedAt,
    };

_$PatientListResponseImpl _$$PatientListResponseImplFromJson(
        Map<String, dynamic> json) =>
    _$PatientListResponseImpl(
      items: (json['items'] as List<dynamic>)
          .map((e) => PatientModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      total: (json['total'] as num).toInt(),
      currentPage: (json['page'] as num).toInt(),
      totalPages: (json['pages'] as num).toInt(),
      pageSize: (json['size'] as num).toInt(),
    );

Map<String, dynamic> _$$PatientListResponseImplToJson(
        _$PatientListResponseImpl instance) =>
    <String, dynamic>{
      'items': instance.items,
      'total': instance.total,
      'page': instance.currentPage,
      'pages': instance.totalPages,
      'size': instance.pageSize,
    };
