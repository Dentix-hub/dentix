import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../domain/usecases/appointment_usecases.dart';
import 'appointment_notifier.dart';

final patientAppointmentsProvider = StateNotifierProvider.family<PatientAppointmentsNotifier, AppointmentState, int>((ref, patientId) {
  return PatientAppointmentsNotifier(
    getAppointmentsUseCase: ref.watch(getAppointmentsUseCaseProvider),
    patientId: patientId,
  );
});

class PatientAppointmentsNotifier extends StateNotifier<AppointmentState> {
  final GetAppointmentsUseCase _getAppointmentsUseCase;
  final int patientId;

  PatientAppointmentsNotifier({
    required GetAppointmentsUseCase getAppointmentsUseCase,
    required this.patientId,
  })  : _getAppointmentsUseCase = getAppointmentsUseCase,
        super(const AppointmentState.initial());

  Future<void> loadAppointments({bool refresh = false}) async {
    final isInitial = state == const AppointmentState.initial();
    if (!isInitial && !refresh) return;

    state = const AppointmentState.loading();

    final result = await _getAppointmentsUseCase(
      page: 1,
      limit: 50, // Load more for history
      patientId: patientId,
    );

    result.fold(
      (failure) => state = AppointmentState.error(failure.message),
      (list) => state = AppointmentState.loaded(
        appointments: list.items,
        totalPages: list.totalPages,
        currentPage: list.currentPage,
        hasMore: list.currentPage < list.totalPages,
        selectedDate: null, // Not used for history
      ),
    );
  }
}
