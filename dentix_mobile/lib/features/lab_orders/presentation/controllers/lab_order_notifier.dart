import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

import '../../../../core/di/providers.dart';
import '../../domain/entities/lab_order_entity.dart';
import '../../domain/usecases/create_lab_order.dart';
import '../../domain/usecases/get_lab_orders.dart';

part 'lab_order_notifier.freezed.dart';

@freezed
class LabOrderState with _$LabOrderState {
  const factory LabOrderState.initial() = _Initial;
  const factory LabOrderState.loading() = _Loading;
  const factory LabOrderState.loaded({
    required List<LabOrderEntity> labOrders,
    required int currentPage,
    required int totalPages,
    required bool hasMore,
    LabOrderStatus? filterStatus,
    int? selectedPatientId,
  }) = _Loaded;
  const factory LabOrderState.error(String message) = _Error;
}

class LabOrderNotifier extends StateNotifier<LabOrderState> {
  final GetLabOrdersUseCase _getLabOrdersUseCase;
  final CreateLabOrderUseCase _createLabOrderUseCase;
  final int _pageSize = 20;

  LabOrderNotifier({
    required GetLabOrdersUseCase getLabOrdersUseCase,
    required CreateLabOrderUseCase createLabOrderUseCase,
  })  : _getLabOrdersUseCase = getLabOrdersUseCase,
        _createLabOrderUseCase = createLabOrderUseCase,
        super(const LabOrderState.initial());

  Future<void> loadLabOrders({
    LabOrderStatus? status,
    int? patientId,
    bool refresh = false,
  }) async {
    if (state is _Initial || refresh) {
      state = const LabOrderState.loading();
    }

    final result = await _getLabOrdersUseCase(
      GetLabOrdersParams(
        page: 1,
        limit: _pageSize,
        patientId: patientId,
        status: status,
      ),
    );

    result.fold(
      (failure) => state = LabOrderState.error(failure.message),
      (labOrderList) => state = LabOrderState.loaded(
        labOrders: labOrderList.items,
        currentPage: labOrderList.currentPage,
        totalPages: labOrderList.totalPages,
        hasMore: labOrderList.currentPage < labOrderList.totalPages,
        filterStatus: status,
        selectedPatientId: patientId,
      ),
    );
  }

  Future<void> loadMoreLabOrders() async {
    final currentState = state;
    if (currentState is! _Loaded || !currentState.hasMore) return;

    final result = await _getLabOrdersUseCase(
      GetLabOrdersParams(
        page: currentState.currentPage + 1,
        limit: _pageSize,
        patientId: currentState.selectedPatientId,
        status: currentState.filterStatus,
      ),
    );

    result.fold(
      (failure) => state = LabOrderState.error(failure.message),
      (labOrderList) => state = LabOrderState.loaded(
        labOrders: [...currentState.labOrders, ...labOrderList.items],
        currentPage: labOrderList.currentPage,
        totalPages: labOrderList.totalPages,
        hasMore: labOrderList.currentPage < labOrderList.totalPages,
        filterStatus: currentState.filterStatus,
        selectedPatientId: currentState.selectedPatientId,
      ),
    );
  }

  Future<bool> createLabOrder({
    required int patientId,
    required String labName,
    required String dueDate,
    required List<Map<String, dynamic>> items,
    String? notes,
  }) async {
    final result = await _createLabOrderUseCase(
      CreateLabOrderParams(
        patientId: patientId,
        labName: labName,
        dueDate: dueDate,
        items: items,
        notes: notes,
      ),
    );

    return result.fold(
      (failure) {
        state = LabOrderState.error(failure.message);
        return false;
      },
      (_) {
        loadLabOrders(
          status: (state as _Loaded?)?.filterStatus,
          patientId: (state as _Loaded?)?.selectedPatientId,
        );
        return true;
      },
    );
  }
}

final labOrderNotifierProvider =
    StateNotifierProvider<LabOrderNotifier, LabOrderState>((ref) {
  final getLabOrdersUseCase = ref.watch(getLabOrdersUseCaseProvider);
  final createLabOrderUseCase = ref.watch(createLabOrderUseCaseProvider);

  return LabOrderNotifier(
    getLabOrdersUseCase: getLabOrdersUseCase,
    createLabOrderUseCase: createLabOrderUseCase,
  );
});
