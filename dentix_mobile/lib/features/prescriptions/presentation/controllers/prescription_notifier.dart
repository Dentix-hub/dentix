import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

import '../../../../core/di/providers.dart';
import '../../domain/entities/prescription_entity.dart';
import '../../domain/usecases/create_prescription.dart';
import '../../domain/usecases/get_prescriptions.dart';

part 'prescription_notifier.freezed.dart';

/// State for prescription notifier
@freezed
class PrescriptionState with _$PrescriptionState {
  const factory PrescriptionState.initial() = _Initial;
  const factory PrescriptionState.loading() = _Loading;
  const factory PrescriptionState.loaded({
    required List<PrescriptionEntity> prescriptions,
    required int currentPage,
    required int totalPages,
    required bool hasMore,
    int? selectedPatientId,
  }) = _Loaded;
  const factory PrescriptionState.error(String message) = _Error;
}

/// Notifier for prescription operations
class PrescriptionNotifier extends StateNotifier<PrescriptionState> {
  final GetPrescriptionsUseCase _getPrescriptionsUseCase;
  final CreatePrescriptionUseCase _createPrescriptionUseCase;
  final int _pageSize = 20;

  PrescriptionNotifier({
    required GetPrescriptionsUseCase getPrescriptionsUseCase,
    required CreatePrescriptionUseCase createPrescriptionUseCase,
  })  : _getPrescriptionsUseCase = getPrescriptionsUseCase,
        _createPrescriptionUseCase = createPrescriptionUseCase,
        super(const PrescriptionState.initial());

  /// Load prescriptions
  Future<void> loadPrescriptions({
    int? patientId,
    bool refresh = false,
  }) async {
    if (state is _Initial || refresh) {
      state = const PrescriptionState.loading();
    }

    final result = await _getPrescriptionsUseCase(
      GetPrescriptionsParams(
        page: 1,
        limit: _pageSize,
        patientId: patientId,
      ),
    );

    result.fold(
      (failure) => state = PrescriptionState.error(failure.message),
      (prescriptionList) => state = PrescriptionState.loaded(
        prescriptions: prescriptionList.items,
        currentPage: prescriptionList.currentPage,
        totalPages: prescriptionList.totalPages,
        hasMore: prescriptionList.currentPage < prescriptionList.totalPages,
        selectedPatientId: patientId,
      ),
    );
  }

  /// Load more prescriptions (pagination)
  Future<void> loadMorePrescriptions() async {
    final currentState = state;
    if (currentState is! _Loaded || !currentState.hasMore) return;

    final result = await _getPrescriptionsUseCase(
      GetPrescriptionsParams(
        page: currentState.currentPage + 1,
        limit: _pageSize,
        patientId: currentState.selectedPatientId,
      ),
    );

    result.fold(
      (failure) => state = PrescriptionState.error(failure.message),
      (prescriptionList) => state = PrescriptionState.loaded(
        prescriptions: [
          ...currentState.prescriptions,
          ...prescriptionList.items,
        ],
        currentPage: prescriptionList.currentPage,
        totalPages: prescriptionList.totalPages,
        hasMore: prescriptionList.currentPage < prescriptionList.totalPages,
        selectedPatientId: currentState.selectedPatientId,
      ),
    );
  }

  /// Create a new prescription
  Future<bool> createPrescription({
    required int patientId,
    required List<Map<String, dynamic>> medications,
    String? notes,
  }) async {
    final result = await _createPrescriptionUseCase(
      CreatePrescriptionParams(
        patientId: patientId,
        medications: medications,
        notes: notes,
      ),
    );

    return result.fold(
      (failure) {
        state = PrescriptionState.error(failure.message);
        return false;
      },
      (prescription) {
        // Refresh the list after creating
        loadPrescriptions(patientId: (state as _Loaded?)?.selectedPatientId);
        return true;
      },
    );
  }
}

/// Provider for prescription notifier
final prescriptionNotifierProvider =
    StateNotifierProvider<PrescriptionNotifier, PrescriptionState>((ref) {
  final getPrescriptionsUseCase = ref.watch(getPrescriptionsUseCaseProvider);
  final createPrescriptionUseCase = ref.watch(createPrescriptionUseCaseProvider);

  return PrescriptionNotifier(
    getPrescriptionsUseCase: getPrescriptionsUseCase,
    createPrescriptionUseCase: createPrescriptionUseCase,
  );
});
