import 'package:dio/dio.dart';

import '../../../../core/constants/api_endpoints.dart';
import '../../../../core/error/exceptions.dart';
import '../models/treatment_model.dart';

abstract class TreatmentRemoteDataSource {
  Future<TreatmentListResponse> getTreatmentsByPatientId({
    required int patientId,
    required int page,
    required int limit,
  });
  
  Future<TreatmentModel> getTreatmentById(int id);
}

class TreatmentRemoteDataSourceImpl implements TreatmentRemoteDataSource {
  final Dio dio;

  TreatmentRemoteDataSourceImpl({required this.dio});

  @override
  Future<TreatmentListResponse> getTreatmentsByPatientId({
    required int patientId,
    required int page,
    required int limit,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'skip': (page - 1) * limit,
        'limit': limit,
        'patient_id': patientId,
      };

      final response = await dio.get(
        ApiEndpoints.treatments,
        queryParameters: queryParams,
      );

      if (response.statusCode == 200) {
        return TreatmentListResponse.fromJson(response.data as Map<String, dynamic>);
      } else {
        throw ServerException(
          message: 'Failed to load treatments',
          code: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw ServerException(
        message: e.response?.data?['message'] ?? 'Network error',
        code: e.response?.statusCode,
      );
    }
  }

  @override
  Future<TreatmentModel> getTreatmentById(int id) async {
    try {
      final response = await dio.get('${ApiEndpoints.treatments}/$id');

      if (response.statusCode == 200) {
        return TreatmentModel.fromJson(response.data as Map<String, dynamic>);
      } else {
        throw ServerException(
          message: 'Failed to load treatment',
          code: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw ServerException(
        message: e.response?.data?['message'] ?? 'Network error',
        code: e.response?.statusCode,
      );
    }
  }
}
