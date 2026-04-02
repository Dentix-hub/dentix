import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../../core/l10n/app_localizations.dart';
import '../../../../core/theme/app_colors.dart';
import '../../domain/entities/lab_order_entity.dart';
import '../controllers/lab_order_notifier.dart';
import 'create_lab_order_page.dart';

class LabOrdersListPage extends ConsumerStatefulWidget {
  const LabOrdersListPage({super.key});

  @override
  ConsumerState<LabOrdersListPage> createState() => _LabOrdersListPageState();
}

class _LabOrdersListPageState extends ConsumerState<LabOrdersListPage> {
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent - 200) {
      ref.read(labOrderNotifierProvider.notifier).loadMoreLabOrders();
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final state = ref.watch(labOrderNotifierProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.labOrders),
        actions: [
          // Status filter
          PopupMenuButton<LabOrderStatus?>(
            icon: const Icon(Icons.filter_list),
            onSelected: (status) {
              ref.read(labOrderNotifierProvider.notifier).loadLabOrders(
                    status: status,
                  );
            },
            itemBuilder: (context) => [
              PopupMenuItem(
                value: null,
                child: Text(l10n.all),
              ),
              ...LabOrderStatus.values.map((status) => PopupMenuItem(
                    value: status,
                    child: Text(_getStatusLabel(status)),
                  )),
            ],
          ),
        ],
      ),
      body: state.when(
        initial: () {
          Future.microtask(() {
            ref.read(labOrderNotifierProvider.notifier).loadLabOrders();
          });
          return const SizedBox.shrink();
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (message) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error_outline, size: 64, color: AppColors.error),
              const SizedBox(height: 16),
              Text(message),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () {
                  ref.read(labOrderNotifierProvider.notifier).loadLabOrders();
                },
                child: Text(l10n.retry),
              ),
            ],
          ),
        ),
        loaded: (labOrders, currentPage, totalPages, hasMore, filterStatus,
            selectedPatientId) {
          if (labOrders.isEmpty) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.science_outlined,
                      size: 64, color: AppColors.textDisabled),
                  const SizedBox(height: 16),
                  Text(
                    l10n.noLabOrders,
                    style: TextStyle(color: AppColors.textSecondary),
                  ),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: () async {
              await ref
                  .read(labOrderNotifierProvider.notifier)
                  .loadLabOrders(status: filterStatus, refresh: true);
            },
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.all(16),
              itemCount: labOrders.length + (hasMore ? 1 : 0),
              itemBuilder: (context, index) {
                if (index >= labOrders.length) {
                  return const Padding(
                    padding: EdgeInsets.all(16),
                    child: Center(child: CircularProgressIndicator()),
                  );
                }
                return _buildLabOrderCard(labOrders[index]);
              },
            ),
          );
        },
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _showCreateLabOrderDialog(context),
        icon: const Icon(Icons.add),
        label: Text(l10n.createLabOrder),
      ),
    );
  }

  Widget _buildLabOrderCard(LabOrderEntity labOrder) {
    final l10n = AppLocalizations.of(context)!;
    final statusColor = _getStatusColor(labOrder.status);
    final isOverdue = labOrder.isOverdue;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        labOrder.labName,
                        style: const TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        labOrder.patientName ??
                            l10n.patientNumber(labOrder.patientId),
                        style: TextStyle(
                          color: AppColors.textSecondary,
                          fontSize: 14,
                        ),
                      ),
                    ],
                  ),
                ),
                Chip(
                  label: Text(
                    _getStatusLabel(labOrder.status),
                    style: const TextStyle(fontSize: 12, color: Colors.white),
                  ),
                  backgroundColor: statusColor,
                ),
              ],
            ),
            const Divider(height: 24),
            // Work items
            ...labOrder.items.map((item) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(
                    children: [
                      Icon(Icons.check_circle_outline,
                          size: 16, color: AppColors.primary),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          '${item.workType} x${item.quantity}',
                          style: const TextStyle(fontWeight: FontWeight.w500),
                        ),
                      ),
                    ],
                  ),
                )),
            const SizedBox(height: 12),
            // Due date
            Row(
              children: [
                Icon(
                  Icons.calendar_today,
                  size: 16,
                  color: isOverdue ? AppColors.error : AppColors.textSecondary,
                ),
                const SizedBox(width: 8),
                Text(
                  '${AppLocalizations.of(context)!.dueDate}: ${DateFormat('MMM d, yyyy').format(DateTime.parse(labOrder.dueDate))}',
                  style: TextStyle(
                    color: isOverdue ? AppColors.error : AppColors.textSecondary,
                    fontWeight: isOverdue ? FontWeight.bold : null,
                  ),
                ),
                if (isOverdue) ...[
                  const SizedBox(width: 8),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: AppColors.error.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      AppLocalizations.of(context)!.overdue,
                      style: TextStyle(
                        color: AppColors.error,
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }

  Color _getStatusColor(LabOrderStatus status) {
    return switch (status) {
      LabOrderStatus.pending => AppColors.warning,
      LabOrderStatus.inProgress => AppColors.primary,
      LabOrderStatus.completed => AppColors.success,
      LabOrderStatus.cancelled => AppColors.error,
    };
  }

  String _getStatusLabel(LabOrderStatus status) {
    final l10n = AppLocalizations.of(context)!;
    return switch (status) {
      LabOrderStatus.pending => l10n.statusPending,
      LabOrderStatus.inProgress => l10n.statusInProgress,
      LabOrderStatus.completed => l10n.statusCompleted,
      LabOrderStatus.cancelled => l10n.statusCancelled,
    };
  }

  void _showCreateLabOrderDialog(BuildContext context) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => const CreateLabOrderPage(),
      ),
    );
  }
}
