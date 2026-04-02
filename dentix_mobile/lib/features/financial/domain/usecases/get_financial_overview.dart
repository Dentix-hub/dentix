import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../../../../core/usecases/usecase.dart';
import '../entities/financial_transaction_entity.dart';
import '../repositories/financial_repository.dart';

/// Use case to get financial overview with pagination and optional month filter
class GetFinancialOverviewUseCase
    implements UseCase<FinancialOverviewEntity, GetFinancialOverviewParams> {
  final FinancialRepository repository;

  GetFinancialOverviewUseCase(this.repository);

  @override
  Future<Either<Failure, FinancialOverviewEntity>> call(
    GetFinancialOverviewParams params,
  ) async {
    return await repository.getFinancialOverview(
      page: params.page,
      limit: params.limit,
      month: params.month,
    );
  }
}

/// Parameters for GetFinancialOverviewUseCase
class GetFinancialOverviewParams {
  final int page;
  final int limit;
  final String? month;

  GetFinancialOverviewParams({
    required this.page,
    required this.limit,
    this.month,
  });
}
