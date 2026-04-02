import 'package:dio/dio.dart';

import '../../../../core/constants/api_endpoints.dart';
import '../../../../core/network/dio_client.dart';
import '../models/financial_transaction_model.dart';

/// Remote data source for financial operations
class FinancialRemoteDataSource {
  final Dio _dio;

  FinancialRemoteDataSource({Dio? dio}) : _dio = dio ?? DioClient.dio;

  /// Get financial overview with pagination and optional month filter
  Future<FinancialOverviewResponseModel> getFinancialOverview({
    required int page,
    required int limit,
    String? month,
  }) async {
    final response = await _dio.get(
      ApiEndpoints.financialOverview,
      queryParameters: {
        'page': page,
        'limit': limit,
        if (month != null) 'month': month,
      },
    );

    return FinancialOverviewResponseModel.fromJson(response.data);
  }

  /// Record a new payment/transaction
  Future<FinancialTransactionModel> recordPayment({
    required int patientId,
    required double amount,
    required String date,
    String? description,
    int? appointmentId,
    int? treatmentId,
  }) async {
    final request = RecordPaymentRequestModel(
      patientId: patientId,
      amount: amount,
      date: date,
      description: description,
      appointmentId: appointmentId,
      treatmentId: treatmentId,
    );

    final response = await _dio.post(
      ApiEndpoints.recordPayment,
      data: request.toJson(),
    );

    return FinancialTransactionModel.fromJson(response.data);
  }
}
