import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../../../../core/usecases/usecase.dart';
import '../entities/financial_transaction_entity.dart';
import '../repositories/financial_repository.dart';

/// Use case to record a new payment/transaction
class RecordPaymentUseCase
    implements UseCase<FinancialTransactionEntity, RecordPaymentParams> {
  final FinancialRepository repository;

  RecordPaymentUseCase(this.repository);

  @override
  Future<Either<Failure, FinancialTransactionEntity>> call(
    RecordPaymentParams params,
  ) async {
    return await repository.recordPayment(
      patientId: params.patientId,
      amount: params.amount,
      date: params.date,
      description: params.description,
      appointmentId: params.appointmentId,
      treatmentId: params.treatmentId,
    );
  }
}

/// Parameters for RecordPaymentUseCase
class RecordPaymentParams {
  final int patientId;
  final double amount;
  final String date;
  final String? description;
  final int? appointmentId;
  final int? treatmentId;

  RecordPaymentParams({
    required this.patientId,
    required this.amount,
    required this.date,
    this.description,
    this.appointmentId,
    this.treatmentId,
  });
}
