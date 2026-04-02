// ignore_for_file: invalid_annotation_target
import 'package:freezed_annotation/freezed_annotation.dart';

part 'treatment_model.freezed.dart';
part 'treatment_model.g.dart';

@freezed
class TreatmentModel with _$TreatmentModel {
  const factory TreatmentModel({
    required int id,
    @JsonKey(name: 'patient_id') required int patientId,
    @JsonKey(name: 'appointment_id') int? appointmentId,
    @JsonKey(name: 'procedure_type') required String procedureType,
    @JsonKey(name: 'description') String? description,
    @JsonKey(name: 'cost') required double cost,
    @JsonKey(name: 'status') required String status,
    @JsonKey(name: 'treatment_date') required String treatmentDate,
    @JsonKey(name: 'created_at') String? createdAt,
    @JsonKey(name: 'updated_at') String? updatedAt,
  }) = _TreatmentModel;

  factory TreatmentModel.fromJson(Map<String, dynamic> json) =>
      _$TreatmentModelFromJson(json);
}

@freezed
class TreatmentListResponse with _$TreatmentListResponse {
  const factory TreatmentListResponse({
    required List<TreatmentModel> items,
    required int total,
    @JsonKey(name: 'page') required int currentPage,
    @JsonKey(name: 'pages') required int totalPages,
  }) = _TreatmentListResponse;

  factory TreatmentListResponse.fromJson(Map<String, dynamic> json) =>
      _$TreatmentListResponseFromJson(json);
}
