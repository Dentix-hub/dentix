import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

import '../../../../core/di/providers.dart';
import '../../domain/entities/financial_transaction_entity.dart';
import '../../domain/usecases/get_financial_overview.dart';
import '../../domain/usecases/record_payment.dart';

part 'financial_notifier.freezed.dart';

/// State for financial notifier
@freezed
class FinancialState with _$FinancialState {
  const factory FinancialState.initial() = _Initial;
  const factory FinancialState.loading() = _Loading;
  const factory FinancialState.loaded({
    required List<FinancialTransactionEntity> transactions,
    required int totalRevenue,
    required int totalExpenses,
    required double netIncome,
    required int currentPage,
    required int totalPages,
    required bool hasMore,
    String? selectedMonth,
  }) = _Loaded;
  const factory FinancialState.error(String message) = _Error;
}

/// Notifier for financial operations
class FinancialNotifier extends StateNotifier<FinancialState> {
  final GetFinancialOverviewUseCase _getFinancialOverviewUseCase;
  final RecordPaymentUseCase _recordPaymentUseCase;
  final int _pageSize = 20;

  FinancialNotifier({
    required GetFinancialOverviewUseCase getFinancialOverviewUseCase,
    required RecordPaymentUseCase recordPaymentUseCase,
  })  : _getFinancialOverviewUseCase = getFinancialOverviewUseCase,
        _recordPaymentUseCase = recordPaymentUseCase,
        super(const FinancialState.initial());

  /// Load financial overview
  Future<void> loadFinancialOverview({
    String? month,
    bool refresh = false,
  }) async {
    if (state is _Initial || refresh) {
      state = const FinancialState.loading();
    }

    final result = await _getFinancialOverviewUseCase(
      GetFinancialOverviewParams(
        page: 1,
        limit: _pageSize,
        month: month,
      ),
    );

    result.fold(
      (failure) => state = FinancialState.error(failure.message),
      (overview) => state = FinancialState.loaded(
        transactions: overview.items,
        totalRevenue: overview.totalRevenue,
        totalExpenses: overview.totalExpenses,
        netIncome: overview.netIncome,
        currentPage: overview.currentPage,
        totalPages: overview.totalPages,
        hasMore: overview.currentPage < overview.totalPages,
        selectedMonth: month,
      ),
    );
  }

  /// Load more transactions (pagination)
  Future<void> loadMoreTransactions() async {
    final currentState = state;
    if (currentState is! _Loaded || !currentState.hasMore) return;

    final result = await _getFinancialOverviewUseCase(
      GetFinancialOverviewParams(
        page: currentState.currentPage + 1,
        limit: _pageSize,
        month: currentState.selectedMonth,
      ),
    );

    result.fold(
      (failure) => state = FinancialState.error(failure.message),
      (overview) => state = FinancialState.loaded(
        transactions: [...currentState.transactions, ...overview.items],
        totalRevenue: overview.totalRevenue,
        totalExpenses: overview.totalExpenses,
        netIncome: overview.netIncome,
        currentPage: overview.currentPage,
        totalPages: overview.totalPages,
        hasMore: overview.currentPage < overview.totalPages,
        selectedMonth: currentState.selectedMonth,
      ),
    );
  }

  /// Record a new payment
  Future<bool> recordPayment({
    required int patientId,
    required double amount,
    required String date,
    String? description,
    int? appointmentId,
    int? treatmentId,
  }) async {
    final result = await _recordPaymentUseCase(
      RecordPaymentParams(
        patientId: patientId,
        amount: amount,
        date: date,
        description: description,
        appointmentId: appointmentId,
        treatmentId: treatmentId,
      ),
    );

    return result.fold(
      (failure) {
        state = FinancialState.error(failure.message);
        return false;
      },
      (transaction) {
        // Refresh the list after recording payment
        loadFinancialOverview(month: (state as _Loaded?)?.selectedMonth);
        return true;
      },
    );
  }
}

/// Provider for financial notifier
final financialNotifierProvider =
    StateNotifierProvider<FinancialNotifier, FinancialState>((ref) {
  final getFinancialOverviewUseCase =
      ref.watch(getFinancialOverviewUseCaseProvider);
  final recordPaymentUseCase = ref.watch(recordPaymentUseCaseProvider);

  return FinancialNotifier(
    getFinancialOverviewUseCase: getFinancialOverviewUseCase,
    recordPaymentUseCase: recordPaymentUseCase,
  );
});
