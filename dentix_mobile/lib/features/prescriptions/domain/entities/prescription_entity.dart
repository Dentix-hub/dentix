import 'package:freezed_annotation/freezed_annotation.dart';

part 'prescription_entity.freezed.dart';

/// Prescription entity representing a medical prescription
@freezed
class PrescriptionEntity with _$PrescriptionEntity {
  const factory PrescriptionEntity({
    required int id,
    required int patientId,
    String? patientName,
    required int dentistId,
    String? dentistName,
    required String prescriptionDate,
    required List<PrescribedMedicationEntity> medications,
    String? notes,
    String? status,
    String? createdAt,
    String? updatedAt,
  }) = _PrescriptionEntity;

  const PrescriptionEntity._();
}

/// Medication prescribed in a prescription
@freezed
class PrescribedMedicationEntity with _$PrescribedMedicationEntity {
  const factory PrescribedMedicationEntity({
    required int id,
    required int medicationId,
    String? medicationName,
    String? dosage,
    String? frequency,
    String? duration,
    String? instructions,
  }) = _PrescribedMedicationEntity;

  const PrescribedMedicationEntity._();
}

/// Paginated list of prescriptions
@freezed
class PrescriptionListEntity with _$PrescriptionListEntity {
  const factory PrescriptionListEntity({
    required List<PrescriptionEntity> items,
    required int currentPage,
    required int totalPages,
    required int totalItems,
  }) = _PrescriptionListEntity;

  const PrescriptionListEntity._();
}
