import 'package:dio/dio.dart';

import '../../../../core/constants/api_endpoints.dart';
import '../../../../core/network/dio_client.dart';
import '../models/prescription_model.dart';

/// Remote data source for prescription operations
class PrescriptionRemoteDataSource {
  final Dio _dio;

  PrescriptionRemoteDataSource({Dio? dio}) : _dio = dio ?? DioClient.dio;

  /// Get prescriptions list with pagination
  Future<PrescriptionListResponseModel> getPrescriptions({
    required int page,
    required int limit,
    int? patientId,
  }) async {
    final response = await _dio.get(
      ApiEndpoints.prescriptions,
      queryParameters: {
        'page': page,
        'limit': limit,
        if (patientId != null) 'patient_id': patientId,
      },
    );

    return PrescriptionListResponseModel.fromJson(response.data);
  }

  /// Get a single prescription by ID
  Future<PrescriptionModel> getPrescriptionById(int id) async {
    final response = await _dio.get('${ApiEndpoints.prescriptions}/$id');
    return PrescriptionModel.fromJson(response.data);
  }

  /// Create a new prescription
  Future<PrescriptionModel> createPrescription({
    required int patientId,
    required List<Map<String, dynamic>> medications,
    String? notes,
  }) async {
    final request = CreatePrescriptionRequestModel(
      patientId: patientId,
      medications: medications,
      notes: notes,
    );

    final response = await _dio.post(
      ApiEndpoints.prescriptions,
      data: request.toJson(),
    );

    return PrescriptionModel.fromJson(response.data);
  }

  /// Update an existing prescription
  Future<PrescriptionModel> updatePrescription({
    required int id,
    required List<Map<String, dynamic>> medications,
    String? notes,
  }) async {
    final request = CreatePrescriptionRequestModel(
      patientId: 0, // Not used for update
      medications: medications,
      notes: notes,
    );

    final response = await _dio.put(
      '${ApiEndpoints.prescriptions}/$id',
      data: request.toJson(),
    );

    return PrescriptionModel.fromJson(response.data);
  }

  /// Delete a prescription
  Future<void> deletePrescription(int id) async {
    await _dio.delete('${ApiEndpoints.prescriptions}/$id');
  }
}
