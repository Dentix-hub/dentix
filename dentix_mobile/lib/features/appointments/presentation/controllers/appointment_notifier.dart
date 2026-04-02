import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

import '../../../../core/network/dio_client.dart';
import '../../data/datasources/appointment_remote.dart';
import '../../data/repositories/appointment_repo_impl.dart';
import '../../domain/entities/appointment_entity.dart';
import '../../domain/usecases/appointment_usecases.dart';

part 'appointment_notifier.freezed.dart';

@freezed
class AppointmentState with _$AppointmentState {
  const factory AppointmentState.initial() = _Initial;
  const factory AppointmentState.loading() = _Loading;
  const factory AppointmentState.loaded({
    required List<AppointmentEntity> appointments,
    required int totalPages,
    required int currentPage,
    required bool hasMore,
    String? selectedDate,
  }) = _Loaded;
  const factory AppointmentState.error(String message) = _Error;
}

// Providers
final appointmentRemoteDataSourceProvider = Provider((ref) {
  return AppointmentRemoteDataSourceImpl(dio: DioClient.dio);
});

final appointmentRepositoryProvider = Provider((ref) {
  return AppointmentRepositoryImpl(
    remoteDataSource: ref.watch(appointmentRemoteDataSourceProvider),
  );
});

final getAppointmentsUseCaseProvider = Provider((ref) {
  return GetAppointmentsUseCase(
    repository: ref.watch(appointmentRepositoryProvider),
  );
});

final createAppointmentUseCaseProvider = Provider((ref) {
  return CreateAppointmentUseCase(
    repository: ref.watch(appointmentRepositoryProvider),
  );
});

final cancelAppointmentUseCaseProvider = Provider((ref) {
  return CancelAppointmentUseCase(
    repository: ref.watch(appointmentRepositoryProvider),
  );
});

final completeAppointmentUseCaseProvider = Provider((ref) {
  return CompleteAppointmentUseCase(
    repository: ref.watch(appointmentRepositoryProvider),
  );
});

final appointmentNotifierProvider = StateNotifierProvider<AppointmentNotifier, AppointmentState>((ref) {
  return AppointmentNotifier(
    getAppointmentsUseCase: ref.watch(getAppointmentsUseCaseProvider),
    createAppointmentUseCase: ref.watch(createAppointmentUseCaseProvider),
    cancelAppointmentUseCase: ref.watch(cancelAppointmentUseCaseProvider),
    completeAppointmentUseCase: ref.watch(completeAppointmentUseCaseProvider),
  );
});

class AppointmentNotifier extends StateNotifier<AppointmentState> {
  final GetAppointmentsUseCase _getAppointmentsUseCase;
  final CreateAppointmentUseCase _createAppointmentUseCase;
  final CancelAppointmentUseCase _cancelAppointmentUseCase;
  final CompleteAppointmentUseCase _completeAppointmentUseCase;
  static const int _pageSize = 20;

  AppointmentNotifier({
    required GetAppointmentsUseCase getAppointmentsUseCase,
    required CreateAppointmentUseCase createAppointmentUseCase,
    required CancelAppointmentUseCase cancelAppointmentUseCase,
    required CompleteAppointmentUseCase completeAppointmentUseCase,
  })  : _getAppointmentsUseCase = getAppointmentsUseCase,
        _createAppointmentUseCase = createAppointmentUseCase,
        _cancelAppointmentUseCase = cancelAppointmentUseCase,
        _completeAppointmentUseCase = completeAppointmentUseCase,
        super(const AppointmentState.initial());

  Future<void> loadAppointments({String? date, bool refresh = false}) async {
    if (refresh) {
      state = const AppointmentState.loading();
    }

    final result = await _getAppointmentsUseCase(
      page: 1,
      limit: _pageSize,
      date: date,
    );

    result.fold(
      (failure) => state = AppointmentState.error(failure.message),
      (appointmentList) => state = AppointmentState.loaded(
        appointments: appointmentList.items,
        totalPages: appointmentList.totalPages,
        currentPage: appointmentList.currentPage,
        hasMore: appointmentList.currentPage < appointmentList.totalPages,
        selectedDate: date,
      ),
    );
  }

  Future<void> loadMoreAppointments() async {
    final currentState = state;
    if (currentState is! _Loaded || !currentState.hasMore) return;

    final nextPage = currentState.currentPage + 1;

    final result = await _getAppointmentsUseCase(
      page: nextPage,
      limit: _pageSize,
      date: currentState.selectedDate,
    );

    result.fold(
      (failure) => state = AppointmentState.error(failure.message),
      (appointmentList) => state = AppointmentState.loaded(
        appointments: [...currentState.appointments, ...appointmentList.items],
        totalPages: appointmentList.totalPages,
        currentPage: appointmentList.currentPage,
        hasMore: appointmentList.currentPage < appointmentList.totalPages,
        selectedDate: currentState.selectedDate,
      ),
    );
  }

  Future<void> selectDate(String date) async {
    await loadAppointments(date: date, refresh: true);
  }

  Future<bool> createAppointment({
    required int patientId,
    required int dentistId,
    required String appointmentDate,
    required String startTime,
    String? endTime,
    String? notes,
    String? procedureType,
  }) async {
    state = const AppointmentState.loading();

    final result = await _createAppointmentUseCase(
      patientId: patientId,
      dentistId: dentistId,
      appointmentDate: appointmentDate,
      startTime: startTime,
      endTime: endTime,
      notes: notes,
      procedureType: procedureType,
    );

    return result.fold(
      (failure) {
        state = AppointmentState.error(failure.message);
        return false;
      },
      (appointment) {
        // Refresh appointments after creating
        loadAppointments(date: appointmentDate, refresh: true);
        return true;
      },
    );
  }

  Future<bool> cancelAppointment(int id) async {
    final result = await _cancelAppointmentUseCase(id);

    return result.fold(
      (failure) {
        state = AppointmentState.error(failure.message);
        return false;
      },
      (_) {
        // Refresh current appointments
        final currentState = state;
        if (currentState is _Loaded) {
          loadAppointments(date: currentState.selectedDate, refresh: true);
        }
        return true;
      },
    );
  }

  Future<bool> completeAppointment(int id) async {
    final result = await _completeAppointmentUseCase(id);

    return result.fold(
      (failure) {
        state = AppointmentState.error(failure.message);
        return false;
      },
      (_) {
        // Refresh current appointments
        final currentState = state;
        if (currentState is _Loaded) {
          loadAppointments(date: currentState.selectedDate, refresh: true);
        }
        return true;
      },
    );
  }
}
