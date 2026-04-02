import 'package:freezed_annotation/freezed_annotation.dart';

import '../../domain/entities/prescription_entity.dart';

part 'prescription_model.freezed.dart';
part 'prescription_model.g.dart';

/// Model for prescribed medication from API
@freezed
class PrescribedMedicationModel with _$PrescribedMedicationModel {
  const factory PrescribedMedicationModel({
    required int id,
    @JsonKey(name: 'medication_id') required int medicationId,
    @JsonKey(name: 'medication_name') String? medicationName,
    String? dosage,
    String? frequency,
    String? duration,
    String? instructions,
  }) = _PrescribedMedicationModel;

  const PrescribedMedicationModel._();

  factory PrescribedMedicationModel.fromJson(Map<String, dynamic> json) =>
      _$PrescribedMedicationModelFromJson(json);

  /// Convert model to entity
  PrescribedMedicationEntity toEntity() {
    return PrescribedMedicationEntity(
      id: id,
      medicationId: medicationId,
      medicationName: medicationName,
      dosage: dosage,
      frequency: frequency,
      duration: duration,
      instructions: instructions,
    );
  }
}

/// Model for prescription from API
@freezed
class PrescriptionModel with _$PrescriptionModel {
  const factory PrescriptionModel({
    required int id,
    @JsonKey(name: 'patient_id') required int patientId,
    @JsonKey(name: 'patient_name') String? patientName,
    @JsonKey(name: 'dentist_id') required int dentistId,
    @JsonKey(name: 'dentist_name') String? dentistName,
    @JsonKey(name: 'prescription_date') required String prescriptionDate,
    required List<PrescribedMedicationModel> medications,
    String? notes,
    String? status,
    @JsonKey(name: 'created_at') String? createdAt,
    @JsonKey(name: 'updated_at') String? updatedAt,
  }) = _PrescriptionModel;

  const PrescriptionModel._();

  factory PrescriptionModel.fromJson(Map<String, dynamic> json) =>
      _$PrescriptionModelFromJson(json);

  /// Convert model to entity
  PrescriptionEntity toEntity() {
    return PrescriptionEntity(
      id: id,
      patientId: patientId,
      patientName: patientName,
      dentistId: dentistId,
      dentistName: dentistName,
      prescriptionDate: prescriptionDate,
      medications: medications.map((e) => e.toEntity()).toList(),
      notes: notes,
      status: status,
      createdAt: createdAt,
      updatedAt: updatedAt,
    );
  }
}

/// Paginated response model for prescriptions
@freezed
class PrescriptionListResponseModel with _$PrescriptionListResponseModel {
  const factory PrescriptionListResponseModel({
    required List<PrescriptionModel> items,
    @JsonKey(name: 'current_page') required int currentPage,
    @JsonKey(name: 'total_pages') required int totalPages,
    @JsonKey(name: 'total_items') required int totalItems,
  }) = _PrescriptionListResponseModel;

  const PrescriptionListResponseModel._();

  factory PrescriptionListResponseModel.fromJson(Map<String, dynamic> json) =>
      _$PrescriptionListResponseModelFromJson(json);

  /// Convert response to entity
  PrescriptionListEntity toEntity() {
    return PrescriptionListEntity(
      items: items.map((e) => e.toEntity()).toList(),
      currentPage: currentPage,
      totalPages: totalPages,
      totalItems: totalItems,
    );
  }
}

/// Request model for creating a prescription
@freezed
class CreatePrescriptionRequestModel with _$CreatePrescriptionRequestModel {
  const factory CreatePrescriptionRequestModel({
    @JsonKey(name: 'patient_id') required int patientId,
    required List<Map<String, dynamic>> medications,
    String? notes,
  }) = _CreatePrescriptionRequestModel;

  const CreatePrescriptionRequestModel._();

  factory CreatePrescriptionRequestModel.fromJson(Map<String, dynamic> json) =>
      _$CreatePrescriptionRequestModelFromJson(json);
}
