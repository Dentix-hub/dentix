import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

import '../../../../core/network/dio_client.dart';
import '../../data/datasources/patient_remote.dart';
import '../../data/repositories/patient_repo_impl.dart';
import '../../domain/entities/patient_entity.dart';
import '../../domain/usecases/get_patients.dart';

part 'patient_list_notifier.freezed.dart';

@freezed
class PatientListState with _$PatientListState {
  const factory PatientListState.initial() = _Initial;
  const factory PatientListState.loading() = _Loading;
  const factory PatientListState.loaded({
    required List<PatientEntity> patients,
    required int totalPages,
    required int currentPage,
    required bool hasMore,
    required String? searchQuery,
  }) = _Loaded;
  const factory PatientListState.error(String message) = _Error;
}

// Providers
final patientRemoteDataSourceProvider = Provider((ref) {
  return PatientRemoteDataSourceImpl(dio: DioClient.dio);
});

final patientRepositoryProvider = Provider((ref) {
  return PatientRepositoryImpl(
    remoteDataSource: ref.watch(patientRemoteDataSourceProvider),
  );
});

final getPatientsUseCaseProvider = Provider((ref) {
  return GetPatientsUseCase(
    repository: ref.watch(patientRepositoryProvider),
  );
});

final createPatientUseCaseProvider = Provider((ref) {
  return CreatePatientUseCase(
    repository: ref.watch(patientRepositoryProvider),
  );
});

final patientListNotifierProvider = StateNotifierProvider<PatientListNotifier, PatientListState>((ref) {
  return PatientListNotifier(
    getPatientsUseCase: ref.watch(getPatientsUseCaseProvider),
    createPatientUseCase: ref.watch(createPatientUseCaseProvider),
  );
});

class PatientListNotifier extends StateNotifier<PatientListState> {
  final GetPatientsUseCase _getPatientsUseCase;
  final CreatePatientUseCase _createPatientUseCase;
  static const int _pageSize = 20;

  PatientListNotifier({
    required GetPatientsUseCase getPatientsUseCase,
    required CreatePatientUseCase createPatientUseCase,
  })  : _getPatientsUseCase = getPatientsUseCase,
        _createPatientUseCase = createPatientUseCase,
        super(const PatientListState.initial());

  Future<void> loadPatients({String? search, bool refresh = false}) async {
    // Set loading on first load or refresh
    if (state is _Initial || refresh) {
      state = const PatientListState.loading();
    }

    final result = await _getPatientsUseCase(
      page: 1,
      limit: _pageSize,
      search: search,
    );

    result.fold(
      (failure) => state = PatientListState.error(failure.message),
      (patientList) => state = PatientListState.loaded(
        patients: patientList.items,
        totalPages: patientList.totalPages,
        currentPage: patientList.currentPage,
        hasMore: patientList.currentPage < patientList.totalPages,
        searchQuery: search,
      ),
    );
  }

  Future<void> loadMorePatients() async {
    final currentState = state;
    if (currentState is! _Loaded || !currentState.hasMore) return;

    final nextPage = currentState.currentPage + 1;

    final result = await _getPatientsUseCase(
      page: nextPage,
      limit: _pageSize,
      search: currentState.searchQuery,
    );

    result.fold(
      (failure) => state = PatientListState.error(failure.message),
      (patientList) => state = PatientListState.loaded(
        patients: [...currentState.patients, ...patientList.items],
        totalPages: patientList.totalPages,
        currentPage: patientList.currentPage,
        hasMore: patientList.currentPage < patientList.totalPages,
        searchQuery: currentState.searchQuery,
      ),
    );
  }

  Future<void> searchPatients(String query) async {
    await loadPatients(search: query.isEmpty ? null : query, refresh: true);
  }

  Future<bool> createPatient({
    required String fullName,
    required String phone,
    String? email,
    String? gender,
    String? birthDate,
    String? address,
  }) async {
    state = const PatientListState.loading();

    final result = await _createPatientUseCase(
      fullName: fullName,
      phone: phone,
      email: email,
      gender: gender,
      birthDate: birthDate,
      address: address,
    );

    return result.fold(
      (failure) {
        state = PatientListState.error(failure.message);
        return false;
      },
      (patient) {
        // Refresh list
        loadPatients(refresh: true);
        return true;
      },
    );
  }
}
