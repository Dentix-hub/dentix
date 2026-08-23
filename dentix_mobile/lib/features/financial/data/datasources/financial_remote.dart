import 'package:dio/dio.dart';

import '../../../../core/constants/api_endpoints.dart';
import '../../../../core/network/dio_client.dart';
import '../models/financial_transaction_model.dart';

/// Remote data source for financial operations.
///
/// Contract note (HIGH-07): the dedicated /financial/overview and
/// /financial/record-payment routes were never registered server-side.
/// Overview is composed from the real tenant totals (GET /stats/dashboard)
/// plus paged payment rows (GET /payments); recording a payment posts the
/// canonical PaymentCreate contract to POST /payments.
class FinancialRemoteDataSource {
  final Dio _dio;

  FinancialRemoteDataSource({Dio? dio}) : _dio = dio ?? DioClient.dio;

  /// StandardResponse envelopes ({success, data}) unwrap to their payload;
  /// raw payloads (lists, plain maps) pass through untouched.
  dynamic _unwrap(dynamic data) {
    if (data is Map && data.containsKey('success') && data.containsKey('data')) {
      return data['data'];
    }
    return data;
  }

  Map<String, dynamic> _asMap(dynamic value) {
    if (value is Map<String, dynamic>) return value;
    if (value is Map) return value.map((k, v) => MapEntry(k.toString(), v));
    return <String, dynamic>{};
  }

  List<dynamic> _asList(dynamic value) =>
      value is List ? value : const <dynamic>[];

  /// Map a backend Payment payload onto the transaction shape expected by
  /// [FinancialTransactionModel.fromJson].
  Map<String, dynamic> _paymentToTransaction(Map<String, dynamic> payment) {
    return <String, dynamic>{
      'id': payment['id'],
      'type': 'revenue',
      'amount': payment['amount'] ?? 0,
      'date': payment['date'],
      'description': payment['notes'],
      'patient_id': payment['patient_id'],
      'patient_name': payment['patient_name'],
      'category': 'payment',
      'created_at': payment['date'],
      'updated_at': payment['date'],
    };
  }

  num _numOf(dynamic value) =>
      value is num ? value : (num.tryParse('$value') ?? 0);

  /// Financial overview: tenant totals + one page of payment items.
  Future<FinancialOverviewResponseModel> getFinancialOverview({
    required int page,
    required int limit,
    String? month,
  }) async {
    final statsResponse = await _dio.get(ApiEndpoints.financialOverview);
    final stats = _asMap(_unwrap(statsResponse.data));

    final paymentsResponse = await _dio.get(
      ApiEndpoints.paymentsList,
      queryParameters: {
        'skip': (page - 1) * limit,
        'limit': limit,
        if (month != null) 'start_date': month,
      },
    );
    final paymentsPayload = _unwrap(paymentsResponse.data);
    final payments = _asList(paymentsPayload is Map
        ? paymentsPayload['items']
        : paymentsPayload);

    final totalItems = payments.length;
    final totalPages = limit > 0 ? (totalItems / limit).ceil() : 1;

    return FinancialOverviewResponseModel(
      items: payments
          .map((raw) =>
              FinancialTransactionModel.fromJson(_paymentToTransaction(_asMap(raw))))
          .toList(),
      totalRevenue: _numOf(stats['total_revenue']).toInt(),
      totalExpenses: _numOf(stats['total_expenses']).toInt(),
      netIncome: _numOf(stats['net_profit']).toDouble(),
      currentPage: page,
      totalPages: totalPages < 1 ? 1 : totalPages,
      totalItems: totalItems,
    );
  }

  /// Record a new patient payment via the canonical POST /payments contract.
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
      data: <String, dynamic>{
        'patient_id': patientId,
        'amount': amount,
        'date': date,
        if (description != null) 'notes': description,
      },
    );

    final created = _asMap(_unwrap(response.data));
    return FinancialTransactionModel.fromJson(
      _paymentToTransaction(created.isNotEmpty ? created : request.toJson()),
    );
  }
}
