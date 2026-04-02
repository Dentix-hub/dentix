import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

import '../../../../core/network/dio_client.dart';
import '../../data/datasources/treatment_remote.dart';
import '../../data/repositories/treatment_repo_impl.dart';
import '../../domain/entities/treatment_entity.dart';
import '../../domain/usecases/get_treatments.dart';

part 'treatment_notifier.freezed.dart';

@freezed
class TreatmentState with _$TreatmentState {
  const factory TreatmentState.initial() = _Initial;
  const factory TreatmentState.loading() = _Loading;
  const factory TreatmentState.loaded({
    required List<TreatmentEntity> treatments,
    required int totalPages,
    required int currentPage,
    required bool hasMore,
  }) = _Loaded;
  const factory TreatmentState.error(String message) = _Error;
}

// Providers
final treatmentRemoteDataSourceProvider = Provider((ref) {
  return TreatmentRemoteDataSourceImpl(dio: DioClient.dio);
});

final treatmentRepositoryProvider = Provider((ref) {
  return TreatmentRepositoryImpl(
    remoteDataSource: ref.watch(treatmentRemoteDataSourceProvider),
  );
});

final getTreatmentsByPatientIdUseCaseProvider = Provider((ref) {
  return GetTreatmentsByPatientIdUseCase(
    repository: ref.watch(treatmentRepositoryProvider),
  );
});

final treatmentNotifierProvider = StateNotifierProvider.family<TreatmentNotifier, TreatmentState, int>((ref, patientId) {
  return TreatmentNotifier(
    getTreatmentsUseCase: ref.watch(getTreatmentsByPatientIdUseCaseProvider),
    patientId: patientId,
  );
});

class TreatmentNotifier extends StateNotifier<TreatmentState> {
  final GetTreatmentsByPatientIdUseCase _getTreatmentsUseCase;
  final int patientId;
  static const int _pageSize = 20;

  TreatmentNotifier({
    required GetTreatmentsByPatientIdUseCase getTreatmentsUseCase,
    required this.patientId,
  })  : _getTreatmentsUseCase = getTreatmentsUseCase,
        super(const TreatmentState.initial());

  Future<void> loadTreatments({bool refresh = false}) async {
    if (refresh) {
      state = const TreatmentState.loading();
    }

    final result = await _getTreatmentsUseCase(
      patientId: patientId,
      page: 1,
      limit: _pageSize,
    );

    result.fold(
      (failure) => state = TreatmentState.error(failure.message),
      (treatmentList) => state = TreatmentState.loaded(
        treatments: treatmentList.items,
        totalPages: treatmentList.totalPages,
        currentPage: treatmentList.currentPage,
        hasMore: treatmentList.currentPage < treatmentList.totalPages,
      ),
    );
  }

  Future<void> loadMoreTreatments() async {
    final currentState = state;
    if (currentState is! _Loaded || !currentState.hasMore) return;

    final nextPage = currentState.currentPage + 1;

    final result = await _getTreatmentsUseCase(
      patientId: patientId,
      page: nextPage,
      limit: _pageSize,
    );

    result.fold(
      (failure) => state = TreatmentState.error(failure.message),
      (treatmentList) => state = TreatmentState.loaded(
        treatments: [...currentState.treatments, ...treatmentList.items],
        totalPages: treatmentList.totalPages,
        currentPage: treatmentList.currentPage,
        hasMore: treatmentList.currentPage < treatmentList.totalPages,
      ),
    );
  }
}
