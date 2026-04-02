// ignore_for_file: invalid_annotation_target
import 'package:freezed_annotation/freezed_annotation.dart';

part 'appointment_model.freezed.dart';
part 'appointment_model.g.dart';

@freezed
class AppointmentModel with _$AppointmentModel {
  const factory AppointmentModel({
    required int id,
    @JsonKey(name: 'patient_id') required int patientId,
    @JsonKey(name: 'patient_name') String? patientName,
    @JsonKey(name: 'dentist_id') required int dentistId,
    @JsonKey(name: 'dentist_name') String? dentistName,
    @JsonKey(name: 'appointment_date') required String appointmentDate,
    @JsonKey(name: 'start_time') required String startTime,
    @JsonKey(name: 'end_time') String? endTime,
    @JsonKey(name: 'status') required String status, // scheduled, completed, cancelled, no_show
    @JsonKey(name: 'notes') String? notes,
    @JsonKey(name: 'procedure_type') String? procedureType,
    @JsonKey(name: 'created_at') String? createdAt,
    @JsonKey(name: 'updated_at') String? updatedAt,
  }) = _AppointmentModel;

  factory AppointmentModel.fromJson(Map<String, dynamic> json) =>
      _$AppointmentModelFromJson(json);
}

@freezed
class AppointmentListResponse with _$AppointmentListResponse {
  const factory AppointmentListResponse({
    required List<AppointmentModel> items,
    required int total,
    @JsonKey(name: 'page') required int currentPage,
    @JsonKey(name: 'pages') required int totalPages,
  }) = _AppointmentListResponse;

  factory AppointmentListResponse.fromJson(Map<String, dynamic> json) =>
      _$AppointmentListResponseFromJson(json);
}

@freezed
class CreateAppointmentRequest with _$CreateAppointmentRequest {
  const factory CreateAppointmentRequest({
    @JsonKey(name: 'patient_id') required int patientId,
    @JsonKey(name: 'dentist_id') required int dentistId,
    @JsonKey(name: 'appointment_date') required String appointmentDate,
    @JsonKey(name: 'start_time') required String startTime,
    @JsonKey(name: 'end_time') String? endTime,
    @JsonKey(name: 'notes') String? notes,
    @JsonKey(name: 'procedure_type') String? procedureType,
  }) = _CreateAppointmentRequest;

  factory CreateAppointmentRequest.fromJson(Map<String, dynamic> json) =>
      _$CreateAppointmentRequestFromJson(json);
}
