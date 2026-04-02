// ignore_for_file: invalid_annotation_target
import 'package:freezed_annotation/freezed_annotation.dart';

part 'patient_model.freezed.dart';
part 'patient_model.g.dart';

@freezed
class PatientModel with _$PatientModel {
  const factory PatientModel({
    required int id,
    @JsonKey(name: 'full_name') required String fullName,
    @JsonKey(name: 'phone') String? phone,
    @JsonKey(name: 'email') String? email,
    @JsonKey(name: 'date_of_birth') String? dateOfBirth,
    @JsonKey(name: 'gender') String? gender,
    @JsonKey(name: 'address') String? address,
    @JsonKey(name: 'medical_history') String? medicalHistory,
    @JsonKey(name: 'allergies') String? allergies,
    @JsonKey(name: 'created_at') String? createdAt,
    @JsonKey(name: 'updated_at') String? updatedAt,
  }) = _PatientModel;

  factory PatientModel.fromJson(Map<String, dynamic> json) =>
      _$PatientModelFromJson(json);
}

@freezed
class PatientListResponse with _$PatientListResponse {
  const factory PatientListResponse({
    required List<PatientModel> items,
    required int total,
    @JsonKey(name: 'page') required int currentPage,
    @JsonKey(name: 'pages') required int totalPages,
    @JsonKey(name: 'size') required int pageSize,
  }) = _PatientListResponse;

  factory PatientListResponse.fromJson(Map<String, dynamic> json) =>
      _$PatientListResponseFromJson(json);
}
