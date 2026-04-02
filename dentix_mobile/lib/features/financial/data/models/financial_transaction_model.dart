import 'package:freezed_annotation/freezed_annotation.dart';

import '../../domain/entities/financial_transaction_entity.dart';

part 'financial_transaction_model.freezed.dart';
part 'financial_transaction_model.g.dart';

/// Model for financial transaction from API
@freezed
class FinancialTransactionModel with _$FinancialTransactionModel {
  const factory FinancialTransactionModel({
    required int id,
    required String type,
    required double amount,
    required String date,
    String? description,
    @JsonKey(name: 'patient_id') int? patientId,
    @JsonKey(name: 'patient_name') String? patientName,
    @JsonKey(name: 'appointment_id') int? appointmentId,
    @JsonKey(name: 'treatment_id') int? treatmentId,
    String? category,
    @JsonKey(name: 'created_at') String? createdAt,
    @JsonKey(name: 'updated_at') String? updatedAt,
  }) = _FinancialTransactionModel;

  const FinancialTransactionModel._();

  factory FinancialTransactionModel.fromJson(Map<String, dynamic> json) =>
      _$FinancialTransactionModelFromJson(json);

  /// Convert model to entity
  FinancialTransactionEntity toEntity() {
    return FinancialTransactionEntity(
      id: id,
      type: _parseTransactionType(type),
      amount: amount,
      date: date,
      description: description,
      patientId: patientId,
      patientName: patientName,
      appointmentId: appointmentId,
      treatmentId: treatmentId,
      category: category,
      createdAt: createdAt,
      updatedAt: updatedAt,
    );
  }

  /// Parse transaction type string to enum
  static TransactionType _parseTransactionType(String type) {
    return type.toLowerCase() == 'expense' 
        ? TransactionType.expense 
        : TransactionType.revenue;
  }
}

/// Paginated response model for financial overview
@freezed
class FinancialOverviewResponseModel with _$FinancialOverviewResponseModel {
  const factory FinancialOverviewResponseModel({
    required List<FinancialTransactionModel> items,
    @JsonKey(name: 'total_revenue') required int totalRevenue,
    @JsonKey(name: 'total_expenses') required int totalExpenses,
    @JsonKey(name: 'net_income') required double netIncome,
    @JsonKey(name: 'current_page') required int currentPage,
    @JsonKey(name: 'total_pages') required int totalPages,
    @JsonKey(name: 'total_items') required int totalItems,
  }) = _FinancialOverviewResponseModel;

  const FinancialOverviewResponseModel._();

  factory FinancialOverviewResponseModel.fromJson(Map<String, dynamic> json) =>
      _$FinancialOverviewResponseModelFromJson(json);

  /// Convert response to entity
  FinancialOverviewEntity toEntity() {
    return FinancialOverviewEntity(
      items: items.map((e) => e.toEntity()).toList(),
      totalRevenue: totalRevenue,
      totalExpenses: totalExpenses,
      netIncome: netIncome,
      currentPage: currentPage,
      totalPages: totalPages,
      totalItems: totalItems,
    );
  }
}

/// Request model for recording a payment
@freezed
class RecordPaymentRequestModel with _$RecordPaymentRequestModel {
  const factory RecordPaymentRequestModel({
    @JsonKey(name: 'patient_id') required int patientId,
    required double amount,
    required String date,
    String? description,
    @JsonKey(name: 'appointment_id') int? appointmentId,
    @JsonKey(name: 'treatment_id') int? treatmentId,
  }) = _RecordPaymentRequestModel;

  const RecordPaymentRequestModel._();

  factory RecordPaymentRequestModel.fromJson(Map<String, dynamic> json) =>
      _$RecordPaymentRequestModelFromJson(json);
}
