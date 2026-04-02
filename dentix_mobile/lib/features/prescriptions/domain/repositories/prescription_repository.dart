import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../entities/prescription_entity.dart';

/// Repository interface for prescription operations
abstract class PrescriptionRepository {
  /// Get prescriptions list with pagination and optional filters
  ///
  /// [page] - Page number for pagination
  /// [limit] - Items per page
  /// [patientId] - Optional filter by patient
  Future<Either<Failure, PrescriptionListEntity>> getPrescriptions({
    required int page,
    required int limit,
    int? patientId,
  });

  /// Get a single prescription by ID
  Future<Either<Failure, PrescriptionEntity>> getPrescriptionById(int id);

  /// Create a new prescription
  Future<Either<Failure, PrescriptionEntity>> createPrescription({
    required int patientId,
    required List<Map<String, dynamic>> medications,
    String? notes,
  });

  /// Update an existing prescription
  Future<Either<Failure, PrescriptionEntity>> updatePrescription({
    required int id,
    required List<Map<String, dynamic>> medications,
    String? notes,
  });

  /// Delete a prescription
  Future<Either<Failure, void>> deletePrescription(int id);
}
