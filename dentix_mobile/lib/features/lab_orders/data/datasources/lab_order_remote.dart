import 'package:dio/dio.dart';

import '../../../../core/constants/api_endpoints.dart';
import '../../../../core/network/dio_client.dart';
import '../../domain/entities/lab_order_entity.dart';
import '../models/lab_order_model.dart';

class LabOrderRemoteDataSource {
  final Dio _dio;

  LabOrderRemoteDataSource({Dio? dio}) : _dio = dio ?? DioClient.dio;

  Future<LabOrderListResponseModel> getLabOrders({
    required int page,
    required int limit,
    int? patientId,
    LabOrderStatus? status,
  }) async {
    final response = await _dio.get(
      ApiEndpoints.labOrders,
      queryParameters: {
        'page': page,
        'limit': limit,
        if (patientId != null) 'patient_id': patientId,
        if (status != null) 'status': status.name,
      },
    );
    return LabOrderListResponseModel.fromJson(response.data);
  }

  Future<LabOrderModel> getLabOrderById(int id) async {
    final response = await _dio.get('${ApiEndpoints.labOrders}/$id');
    return LabOrderModel.fromJson(response.data);
  }

  Future<LabOrderModel> createLabOrder({
    required int patientId,
    required String labName,
    required String dueDate,
    required List<Map<String, dynamic>> items,
    String? notes,
  }) async {
    final request = CreateLabOrderRequestModel(
      patientId: patientId,
      labName: labName,
      dueDate: dueDate,
      items: items,
      notes: notes,
    );
    final response = await _dio.post(
      ApiEndpoints.labOrders,
      data: request.toJson(),
    );
    return LabOrderModel.fromJson(response.data);
  }

  Future<LabOrderModel> updateLabOrderStatus({
    required int id,
    required LabOrderStatus status,
    String? receivedDate,
  }) async {
    final response = await _dio.patch(
      '${ApiEndpoints.labOrders}/$id/status',
      data: {
        'status': status.name,
        if (receivedDate != null) 'received_date': receivedDate,
      },
    );
    return LabOrderModel.fromJson(response.data);
  }

  Future<void> deleteLabOrder(int id) async {
    await _dio.delete('${ApiEndpoints.labOrders}/$id');
  }
}
