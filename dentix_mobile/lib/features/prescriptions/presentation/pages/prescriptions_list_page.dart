import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../../core/l10n/app_localizations.dart';
import '../../../../core/theme/app_colors.dart';
import '../../domain/entities/prescription_entity.dart';
import '../controllers/prescription_notifier.dart';
import 'create_prescription_page.dart';

class PrescriptionsListPage extends ConsumerStatefulWidget {
  const PrescriptionsListPage({super.key});

  @override
  ConsumerState<PrescriptionsListPage> createState() =>
      _PrescriptionsListPageState();
}

class _PrescriptionsListPageState extends ConsumerState<PrescriptionsListPage> {
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
      ref.read(prescriptionNotifierProvider.notifier).loadMorePrescriptions();
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final state = ref.watch(prescriptionNotifierProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.prescriptions),
      ),
      body: state.when(
        initial: () {
          Future.microtask(() {
            ref.read(prescriptionNotifierProvider.notifier).loadPrescriptions();
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
                  ref
                      .read(prescriptionNotifierProvider.notifier)
                      .loadPrescriptions();
                },
                child: Text(l10n.retry),
              ),
            ],
          ),
        ),
        loaded: (prescriptions, currentPage, totalPages, hasMore, selectedPatientId) {
          if (prescriptions.isEmpty) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.description_outlined,
                      size: 64, color: AppColors.textDisabled),
                  const SizedBox(height: 16),
                  Text(
                    l10n.noPrescriptions,
                    style: TextStyle(color: AppColors.textSecondary),
                  ),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: () async {
              await ref
                  .read(prescriptionNotifierProvider.notifier)
                  .loadPrescriptions(refresh: true);
            },
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.all(16),
              itemCount: prescriptions.length + (hasMore ? 1 : 0),
              itemBuilder: (context, index) {
                if (index >= prescriptions.length) {
                  return const Padding(
                    padding: EdgeInsets.all(16),
                    child: Center(child: CircularProgressIndicator()),
                  );
                }
                return _buildPrescriptionCard(prescriptions[index]);
              },
            ),
          );
        },
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _navigateToCreatePrescription(context),
        icon: const Icon(Icons.add),
        label: Text(l10n.createPrescription),
      ),
    );
  }

  Widget _buildPrescriptionCard(PrescriptionEntity prescription) {
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
                        prescription.patientName ?? 'Patient #${prescription.patientId}',
                        style: const TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        DateFormat('MMM d, yyyy').format(
                          DateTime.parse(prescription.prescriptionDate),
                        ),
                        style: TextStyle(
                          color: AppColors.textSecondary,
                          fontSize: 14,
                        ),
                      ),
                    ],
                  ),
                ),
                if (prescription.status != null)
                  Chip(
                    label: Text(
                      prescription.status!,
                      style: const TextStyle(fontSize: 12),
                    ),
                    backgroundColor: _getStatusColor(prescription.status),
                  ),
              ],
            ),
            const Divider(height: 24),
            // Medications list
            ...prescription.medications.map((med) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(Icons.medication, size: 16, color: AppColors.primary),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              med.medicationName ?? 'Medication #${med.medicationId}',
                              style: const TextStyle(fontWeight: FontWeight.w600),
                            ),
                            if (med.dosage != null)
                              Text(
                                '${med.dosage} • ${med.frequency ?? ''}',
                                style: TextStyle(
                                  color: AppColors.textSecondary,
                                  fontSize: 12,
                                ),
                              ),
                          ],
                        ),
                      ),
                    ],
                  ),
                )),
            if (prescription.notes != null && prescription.notes!.isNotEmpty) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppColors.surface.withOpacity(0.5),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  prescription.notes!,
                  style: TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 12,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Color? _getStatusColor(String? status) {
    return switch (status?.toLowerCase()) {
      'active' => AppColors.success.withOpacity(0.2),
      'completed' => AppColors.primary.withOpacity(0.2),
      'cancelled' => AppColors.error.withOpacity(0.2),
      _ => null,
    };
  }

  void _navigateToCreatePrescription(BuildContext context) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => const CreatePrescriptionPage(),
      ),
    );
  }
}
