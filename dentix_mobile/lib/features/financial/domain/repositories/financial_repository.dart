import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../entities/financial_transaction_entity.dart';

/// Repository interface for financial operations
abstract class FinancialRepository {
  /// Get financial overview with optional month filter
  /// 
  /// [page] - Page number for pagination
  /// [limit] - Items per page
  /// [month] - Optional month filter in format "YYYY-MM"
  Future<Either<Failure, FinancialOverviewEntity>> getFinancialOverview({
    required int page,
    required int limit,
    String? month,
  });

  /// Record a new payment/transaction
  /// 
  /// [patientId] - Patient ID
  /// [amount] - Payment amount
  /// [date] - Payment date
  /// [description] - Optional description
  /// [appointmentId] - Optional related appointment ID
  /// [treatmentId] - Optional related treatment ID
  Future<Either<Failure, FinancialTransactionEntity>> recordPayment({
    required int patientId,
    required double amount,
    required String date,
    String? description,
    int? appointmentId,
    int? treatmentId,
  });
}
