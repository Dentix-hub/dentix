import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/l10n/app_localizations.dart';
import 'package:intl/intl.dart';

import '../../../../core/theme/app_colors.dart';
import '../../domain/entities/patient_entity.dart';
import '../../../treatments/presentation/controllers/treatment_notifier.dart';
import '../../../treatments/domain/entities/treatment_entity.dart';
import '../../../../shared/widgets/empty_state.dart';
import '../../../../shared/widgets/error_retry_widget.dart';
import '../../../appointments/presentation/controllers/patient_appointments_notifier.dart';
import '../../../appointments/domain/entities/appointment_entity.dart';

class PatientDetailPage extends ConsumerStatefulWidget {
  final PatientEntity patient;

  const PatientDetailPage({super.key, required this.patient});

  @override
  ConsumerState<PatientDetailPage> createState() => _PatientDetailPageState();
}

class _PatientDetailPageState extends ConsumerState<PatientDetailPage>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final patient = widget.patient;

    return Scaffold(
      appBar: AppBar(
        title: Text(patient.fullName),
        bottom: TabBar(
          controller: _tabController,
          tabs: [
            Tab(text: l10n.profile, icon: const Icon(Icons.person)),
            Tab(text: l10n.treatments, icon: const Icon(Icons.medical_services)),
            Tab(text: l10n.history, icon: const Icon(Icons.history)),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildProfileTab(patient),
          _buildTreatmentsTab(patient.id),
          _buildHistoryTab(),
        ],
      ),
    );
  }

  Widget _buildProfileTab(PatientEntity patient) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Avatar and Name
          Center(
            child: Column(
              children: [
                CircleAvatar(
                  radius: 50,
                  backgroundColor: AppColors.primary,
                  child: Text(
                    patient.fullName.isNotEmpty
                        ? patient.fullName[0].toUpperCase()
                        : '?',
                    style: const TextStyle(
                      fontSize: 36,
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  patient.fullName,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 32),
          
          // Contact Info
          _buildSectionTitle(AppLocalizations.of(context)!.contactInfo),
          const SizedBox(height: 12),
          _buildInfoRow(Icons.phone, patient.phone ?? AppLocalizations.of(context)!.notAvailable),
          _buildInfoRow(Icons.email, patient.email ?? AppLocalizations.of(context)!.notAvailable),
          _buildInfoRow(Icons.location_on, patient.address ?? AppLocalizations.of(context)!.notAvailable),
          const SizedBox(height: 24),
          
          // Personal Info
          _buildSectionTitle(AppLocalizations.of(context)!.personalInfo),
          const SizedBox(height: 12),
          _buildInfoRow(
            Icons.calendar_today,
            patient.dateOfBirth != null
                ? DateFormat('MMM d, yyyy').format(DateTime.parse(patient.dateOfBirth!))
                : AppLocalizations.of(context)!.notAvailable,
          ),
          _buildInfoRow(Icons.person_outline, patient.gender ?? AppLocalizations.of(context)!.notAvailable),
          const SizedBox(height: 24),
          
          // Medical Info
          _buildSectionTitle(AppLocalizations.of(context)!.medicalInfo),
          const SizedBox(height: 12),
          _buildInfoCard(
            title: AppLocalizations.of(context)!.medicalHistory,
            content: patient.medicalHistory ?? AppLocalizations.of(context)!.noMedicalHistory,
          ),
          const SizedBox(height: 12),
          _buildInfoCard(
            title: AppLocalizations.of(context)!.allergies,
            content: patient.allergies ?? AppLocalizations.of(context)!.noAllergies,
          ),
        ],
      ),
    );
  }

  Widget _buildTreatmentsTab(int patientId) {
    final treatmentState = ref.watch(treatmentNotifierProvider(patientId));

    return treatmentState.when(
      initial: () {
        Future.microtask(() {
          ref.read(treatmentNotifierProvider(patientId).notifier).loadTreatments();
        });
        return const Center(child: CircularProgressIndicator());
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (message) => ErrorRetryWidget(
        message: message,
        onRetry: () {
          ref.read(treatmentNotifierProvider(patientId).notifier).loadTreatments();
        },
      ),
      loaded: (treatments, totalPages, currentPage, hasMore) {
        if (treatments.isEmpty) {
          return EmptyState(
            icon: Icons.medical_services_outlined,
            message: AppLocalizations.of(context)!.noTreatments,
          );
        }

        return RefreshIndicator(
          onRefresh: () async {
            await ref.read(treatmentNotifierProvider(patientId).notifier).loadTreatments(refresh: true);
          },
          child: ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: treatments.length + (hasMore ? 1 : 0),
            itemBuilder: (context, index) {
              if (index >= treatments.length) {
                ref.read(treatmentNotifierProvider(patientId).notifier).loadMoreTreatments();
                return const Padding(
                  padding: EdgeInsets.all(16),
                  child: Center(child: CircularProgressIndicator()),
                );
              }
              return _buildTreatmentCard(treatments[index]);
            },
          ),
        );
      },
    );
  }

  Widget _buildTreatmentCard(TreatmentEntity treatment) {
    Color statusColor = switch (treatment.status.toLowerCase()) {
      'completed' => AppColors.success,
      'pending' => AppColors.warning,
      'in_progress' => AppColors.primary,
      _ => AppColors.textSecondary,
    };

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
                  child: Text(
                    treatment.procedureType,
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 16,
                    ),
                  ),
                ),
                Chip(
                  label: Text(
                    treatment.status,
                    style: const TextStyle(fontSize: 12, color: Colors.white),
                  ),
                  backgroundColor: statusColor,
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              DateFormat('MMM d, yyyy').format(DateTime.parse(treatment.treatmentDate)),
              style: TextStyle(color: AppColors.textSecondary),
            ),
            if (treatment.description != null && treatment.description!.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                treatment.description!,
                style: TextStyle(color: AppColors.textSecondary),
              ),
            ],
            const SizedBox(height: 8),
            Text(
              '\$${treatment.cost.toStringAsFixed(2)}',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: AppColors.primary,
                fontSize: 16,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHistoryTab() {
    return Consumer(
      builder: (context, ref, child) {
        final state = ref.watch(patientAppointmentsProvider(widget.patient.id));

        return state.when(
          initial: () {
            Future.microtask(() => ref.read(patientAppointmentsProvider(widget.patient.id).notifier).loadAppointments());
            return const Center(child: CircularProgressIndicator());
          },
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (message) => ErrorRetryWidget(
            message: message,
            onRetry: () => ref.read(patientAppointmentsProvider(widget.patient.id).notifier).loadAppointments(refresh: true),
          ),
          loaded: (appointments, _, __, ___, ____) {
            if (appointments.isEmpty) {
              return EmptyState(
                icon: Icons.history,
                message: AppLocalizations.of(context)!.noInfoAvailable, // Use generic 'no info' if no specific 'history' key
                subtitle: 'No appointment history available.',
              );
            }
            return ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: appointments.length,
              separatorBuilder: (context, index) => const SizedBox(height: 12),
              itemBuilder: (context, index) {
                final appointment = appointments[index];
                return _buildAppointmentCard(appointment);
              },
            );
          },
        );
      },
    );
  }

  Widget _buildAppointmentCard(AppointmentEntity appointment) {
     return Card(
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: _getStatusColor(appointment.status).withValues(alpha: 0.1),
          child: Icon(_getStatusIcon(appointment.status), color: _getStatusColor(appointment.status), size: 16),
        ),
        title: Text('${appointment.appointmentDate} - ${appointment.startTime}'),
        subtitle: Text(appointment.procedureType ?? 'General Checkup'),
        trailing: Text(
          appointment.status.toUpperCase(),
          style: TextStyle(
            color: _getStatusColor(appointment.status),
            fontWeight: FontWeight.bold,
            fontSize: 12,
          ),
        ),
      ),
    );
  }

  Color _getStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'completed':
        return Colors.green;
      case 'cancelled':
        return Colors.red;
      case 'scheduled':
        return Colors.blue;
      default:
        return Colors.grey;
    }
  }

  IconData _getStatusIcon(String status) {
    switch (status.toLowerCase()) {
      case 'completed':
        return Icons.check;
      case 'cancelled':
        return Icons.close;
      case 'scheduled':
        return Icons.calendar_today;
      default:
        return Icons.info;
    }
  }

  Widget _buildSectionTitle(String title) {
    return Text(
      title,
      style: Theme.of(context).textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
            color: AppColors.primary,
          ),
    );
  }

  Widget _buildInfoRow(IconData icon, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Icon(icon, size: 20, color: AppColors.textSecondary),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              value,
              style: TextStyle(color: AppColors.textSecondary),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoCard({required String title, required String content}) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surface.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.divider),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              fontWeight: FontWeight.w600,
              fontSize: 12,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            content,
            style: TextStyle(color: AppColors.textSecondary),
          ),
        ],
      ),
    );
  }
}
