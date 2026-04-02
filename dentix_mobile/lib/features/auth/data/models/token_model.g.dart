// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'token_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$TokenModelImpl _$$TokenModelImplFromJson(Map<String, dynamic> json) =>
    _$TokenModelImpl(
      accessToken: json['access_token'] as String,
      refreshToken: json['refresh_token'] as String,
      tokenType: json['token_type'] as String?,
      userStatus: json['user_status'] as String?,
      role: json['role'] as String,
      username: json['username'] as String,
    );

Map<String, dynamic> _$$TokenModelImplToJson(_$TokenModelImpl instance) =>
    <String, dynamic>{
      'access_token': instance.accessToken,
      'refresh_token': instance.refreshToken,
      'token_type': instance.tokenType,
      'user_status': instance.userStatus,
      'role': instance.role,
      'username': instance.username,
    };
