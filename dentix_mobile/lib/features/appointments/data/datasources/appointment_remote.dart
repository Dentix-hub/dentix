import 'package:dio/dio.dart';

import '../../../../core/constants/api_endpoints.dart';
import '../../../../core/error/exceptions.dart';
import '../models/appointment_model.dart';

abstract class AppointmentRemoteDataSource {
  Future<AppointmentListResponse> getAppointments({
    required int page,
    required int limit,
    String? date,
    String? startDate,
    String? endDate,
    int? patientId,
  });
  
  Future<AppointmentModel> getAppointmentById(int id);
  
  Future<AppointmentModel> createAppointment(CreateAppointmentRequest request);
  
  Future<AppointmentModel> updateAppointment(int id, CreateAppointmentRequest request);
  
  Future<void> cancelAppointment(int id);
  
  Future<void> completeAppointment(int id);
}

class AppointmentRemoteDataSourceImpl implements AppointmentRemoteDataSource {
  final Dio dio;

  AppointmentRemoteDataSourceImpl({required this.dio});

  @override
  Future<AppointmentListResponse> getAppointments({
    required int page,
    required int limit,
    String? date,
    String? startDate,
    String? endDate,
    int? patientId,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'skip': (page - 1) * limit,
        'limit': limit,
      };
      
      if (date != null) queryParams['date'] = date;
      if (startDate != null) queryParams['start_date'] = startDate;
      if (endDate != null) queryParams['end_date'] = endDate;
      if (patientId != null) queryParams['patient_id'] = patientId;

      final response = await dio.get(
        ApiEndpoints.appointments,
        queryParameters: queryParams,
      );

      if (response.statusCode == 200) {
        return AppointmentListResponse.fromJson(response.data as Map<String, dynamic>);
      } else {
        throw ServerException(
          message: 'Failed to load appointments',
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
  Future<AppointmentModel> getAppointmentById(int id) async {
    try {
      final response = await dio.get('${ApiEndpoints.appointments}/$id');

      if (response.statusCode == 200) {
        return AppointmentModel.fromJson(response.data as Map<String, dynamic>);
      } else {
        throw ServerException(
          message: 'Failed to load appointment',
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
  Future<AppointmentModel> createAppointment(CreateAppointmentRequest request) async {
    try {
      final response = await dio.post(
        ApiEndpoints.appointments,
        data: request.toJson(),
      );

      if (response.statusCode == 201 || response.statusCode == 200) {
        return AppointmentModel.fromJson(response.data as Map<String, dynamic>);
      } else {
        throw ServerException(
          message: 'Failed to create appointment',
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
  Future<AppointmentModel> updateAppointment(int id, CreateAppointmentRequest request) async {
    try {
      final response = await dio.put(
        '${ApiEndpoints.appointments}/$id',
        data: request.toJson(),
      );

      if (response.statusCode == 200) {
        return AppointmentModel.fromJson(response.data as Map<String, dynamic>);
      } else {
        throw ServerException(
          message: 'Failed to update appointment',
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
  Future<void> cancelAppointment(int id) async {
    try {
      final response = await dio.patch(
        '${ApiEndpoints.appointments}/$id/cancel',
      );

      if (response.statusCode != 200) {
        throw ServerException(
          message: 'Failed to cancel appointment',
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
  Future<void> completeAppointment(int id) async {
    try {
      final response = await dio.patch(
        '${ApiEndpoints.appointments}/$id/complete',
      );

      if (response.statusCode != 200) {
        throw ServerException(
          message: 'Failed to complete appointment',
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
