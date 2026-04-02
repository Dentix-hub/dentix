// ignore_for_file: invalid_annotation_target
import 'package:freezed_annotation/freezed_annotation.dart';

part 'user_model.freezed.dart';
part 'user_model.g.dart';

@freezed
class UserModel with _$UserModel {
  const factory UserModel({
    required String id,
    required String username,
    @Default('') String email,
    @Default('user') String role,
    @JsonKey(name: 'tenant_id') String? tenantId,
    @JsonKey(name: 'is_2fa_enabled') @Default(false) bool is2faEnabled,
  }) = _UserModel;

  factory UserModel.fromJson(Map<String, dynamic> json) =>
      _$UserModelFromJson(json);
}
