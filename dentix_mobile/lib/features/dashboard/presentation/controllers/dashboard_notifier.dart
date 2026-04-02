import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

import '../../../../core/network/dio_client.dart';
import '../../data/datasources/dashboard_remote.dart';
import '../../data/repositories/dashboard_repo_impl.dart';
import '../../domain/entities/dashboard_entity.dart';
import '../../domain/usecases/get_dashboard_stats.dart';

part 'dashboard_notifier.freezed.dart';

@freezed
class DashboardState with _$DashboardState {
  const factory DashboardState.initial() = _Initial;
  const factory DashboardState.loading() = _Loading;
  const factory DashboardState.loaded(DashboardStatsEntity stats) = _Loaded;
  const factory DashboardState.error(String message) = _Error;
}

// Providers
final dashboardRemoteDataSourceProvider = Provider((ref) {
  return DashboardRemoteDataSourceImpl(dio: ref.watch(dioProvider));
});

final dashboardRepositoryProvider = Provider((ref) {
  return DashboardRepositoryImpl(
    remoteDataSource: ref.watch(dashboardRemoteDataSourceProvider),
  );
});

final getDashboardStatsUseCaseProvider = Provider((ref) {
  return GetDashboardStatsUseCase(
    repository: ref.watch(dashboardRepositoryProvider),
  );
});

final dashboardNotifierProvider = StateNotifierProvider<DashboardNotifier, DashboardState>((ref) {
  return DashboardNotifier(
    getDashboardStatsUseCase: ref.watch(getDashboardStatsUseCaseProvider),
  );
});

class DashboardNotifier extends StateNotifier<DashboardState> {
  final GetDashboardStatsUseCase _getDashboardStatsUseCase;

  DashboardNotifier({
    required GetDashboardStatsUseCase getDashboardStatsUseCase,
  })  : _getDashboardStatsUseCase = getDashboardStatsUseCase,
        super(const DashboardState.initial());

  Future<void> loadDashboardStats() async {
    state = const DashboardState.loading();

    final result = await _getDashboardStatsUseCase();

    result.fold(
      (failure) => state = DashboardState.error(failure.message),
      (stats) => state = DashboardState.loaded(stats),
    );
  }
}
