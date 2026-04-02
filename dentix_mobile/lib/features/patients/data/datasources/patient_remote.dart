import 'package:dio/dio.dart';

import '../../../../core/constants/api_endpoints.dart';
import '../../../../core/error/exceptions.dart';
import '../models/patient_model.dart';

abstract class PatientRemoteDataSource {
  Future<PatientListResponse> getPatients({
    required int page,
    required int limit,
    String? search,
  });
  
  Future<PatientModel> getPatientById(int id);
  
  Future<PatientModel> createPatient(Map<String, dynamic> data);
}

class PatientRemoteDataSourceImpl implements PatientRemoteDataSource {
  final Dio dio;

  PatientRemoteDataSourceImpl({required this.dio});

  @override
  Future<PatientListResponse> getPatients({
    required int page,
    required int limit,
    String? search,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'skip': (page - 1) * limit,
        'limit': limit,
      };
      
      if (search != null && search.isNotEmpty) {
        queryParams['search'] = search;
      }

      final response = await dio.get(
        ApiEndpoints.patients,
        queryParameters: queryParams,
      );

      if (response.statusCode == 200) {
        return PatientListResponse.fromJson(response.data as Map<String, dynamic>);
      } else {
        throw ServerException(
          message: 'Failed to load patients',
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
  Future<PatientModel> getPatientById(int id) async {
    try {
      final response = await dio.get('${ApiEndpoints.patients}/$id');

      if (response.statusCode == 200) {
        return PatientModel.fromJson(response.data as Map<String, dynamic>);
      } else {
        throw ServerException(
          message: 'Failed to load patient',
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
  Future<PatientModel> createPatient(Map<String, dynamic> data) async {
    try {
      final response = await dio.post(
        ApiEndpoints.patients,
        data: data,
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        return PatientModel.fromJson(response.data as Map<String, dynamic>);
      } else {
        throw ServerException(
          message: 'Failed to create patient',
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
