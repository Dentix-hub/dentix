import 'package:freezed_annotation/freezed_annotation.dart';

part 'financial_transaction_entity.freezed.dart';

/// Financial transaction types
enum TransactionType {
  revenue,
  expense,
}

/// Financial transaction entity representing a single transaction
@freezed
class FinancialTransactionEntity with _$FinancialTransactionEntity {
  const factory FinancialTransactionEntity({
    required int id,
    required TransactionType type,
    required double amount,
    required String date,
    String? description,
    int? patientId,
    String? patientName,
    int? appointmentId,
    int? treatmentId,
    String? category,
    String? createdAt,
    String? updatedAt,
  }) = _FinancialTransactionEntity;

  const FinancialTransactionEntity._();

  /// Check if transaction is revenue
  bool get isRevenue => type == TransactionType.revenue;

  /// Check if transaction is expense
  bool get isExpense => type == TransactionType.expense;

  /// Get formatted amount with sign
  String get formattedAmount {
    final sign = isRevenue ? '+' : '-';
    return '$sign\$${amount.toStringAsFixed(2)}';
  }
}

/// Paginated list of financial transactions
@freezed
class FinancialOverviewEntity with _$FinancialOverviewEntity {
  const factory FinancialOverviewEntity({
    required List<FinancialTransactionEntity> items,
    required int totalRevenue,
    required int totalExpenses,
    required double netIncome,
    required int currentPage,
    required int totalPages,
    required int totalItems,
  }) = _FinancialOverviewEntity;

  const FinancialOverviewEntity._();
}
