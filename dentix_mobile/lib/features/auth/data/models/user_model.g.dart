// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'user_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$UserModelImpl _$$UserModelImplFromJson(Map<String, dynamic> json) =>
    _$UserModelImpl(
      id: json['id'].toString(),
      username: json['username'] as String,
      email: json['email'] as String? ?? '',
      role: json['role'] as String? ?? 'user',
      tenantId: json['tenant_id']?.toString(),
      is2faEnabled: json['is_2fa_enabled'] as bool? ?? false,
    );

Map<String, dynamic> _$$UserModelImplToJson(_$UserModelImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'username': instance.username,
      'email': instance.email,
      'role': instance.role,
      'tenant_id': instance.tenantId,
      'is_2fa_enabled': instance.is2faEnabled,
    };
