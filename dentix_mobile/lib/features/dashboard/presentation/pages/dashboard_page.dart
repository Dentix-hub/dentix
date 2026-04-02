import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../../../core/l10n/app_localizations.dart';

import '../../../../core/theme/app_colors.dart';
import '../controllers/dashboard_notifier.dart';
import '../../../appointments/presentation/controllers/appointment_notifier.dart';
import '../../../appointments/domain/entities/appointment_entity.dart';
import '../../../../shared/widgets/error_retry_widget.dart';

class DashboardPage extends ConsumerStatefulWidget {
  const DashboardPage({super.key});

  @override
  ConsumerState<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends ConsumerState<DashboardPage> {
  @override
  void initState() {
    super.initState();
    _loadData();
  }

  void _loadData() {
    Future.microtask(() {
      ref.read(dashboardNotifierProvider.notifier).loadDashboardStats();
      final today = DateFormat('yyyy-MM-dd').format(DateTime.now());
      ref.read(appointmentNotifierProvider.notifier).loadAppointments(date: today);
    });
  }

  @override
  Widget build(BuildContext context) {
    final dashboardState = ref.watch(dashboardNotifierProvider);
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.dashboard),
        automaticallyImplyLeading: false,
        actions: [
          IconButton(
            onPressed: _loadData,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: SafeArea(
        child: dashboardState.when(
          initial: () => const SizedBox.shrink(),
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (message) => ErrorRetryWidget(
            message: message, 
            onRetry: _loadData,
          ),
          loaded: (stats) => RefreshIndicator(
            onRefresh: () async => _loadData(),
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              physics: const AlwaysScrollableScrollPhysics(),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    l10n.welcomeBack,
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                  const SizedBox(height: 24),
                  _buildStatsGrid(context, stats),
                  const SizedBox(height: 24),
                  _buildQuickActions(context),
                  const SizedBox(height: 24),
                  _buildSectionTitle(context, l10n.todayAppointments),
                  const SizedBox(height: 12),
                  _buildAppointmentsSection(),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildQuickActions(BuildContext context) {
    return SizedBox(
      height: 100,
      child: ListView(
        scrollDirection: Axis.horizontal,
        children: [
          _buildQuickActionCard(
            context,
            icon: Icons.attach_money,
            label: 'Financial', // TODO: Localize
            color: Colors.green,
            onTap: () => context.push('/financial'),
          ),
          _buildQuickActionCard(
            context,
            icon: Icons.medication,
            label: 'Prescriptions', // TODO: Localize
            color: Colors.orange,
            onTap: () => context.push('/prescriptions'),
          ),
          _buildQuickActionCard(
            context,
            icon: Icons.biotech,
            label: 'Lab Orders', // TODO: Localize
            color: Colors.blue,
            onTap: () => context.push('/lab-orders'),
          ),
        ],
      ),
    );
  }

  Widget _buildQuickActionCard(
    BuildContext context, {
    required IconData icon,
    required String label,
    required Color color,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 100,
        margin: const EdgeInsets.only(right: 12),
        decoration: BoxDecoration(
          color: Theme.of(context).cardColor,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.border),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.1),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, color: color, size: 24),
            ),
            const SizedBox(height: 8),
            Text(
              label,
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatsGrid(BuildContext context, dynamic stats) {
    final l10n = AppLocalizations.of(context)!;
    return GridView.count(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisCount: 2,
      mainAxisSpacing: 16,
      crossAxisSpacing: 16,
      childAspectRatio: 1.2,
      children: [
        _buildStatCard(
          icon: Icons.people,
          title: l10n.totalPatients,
          value: stats.totalPatients.toString(),
          color: AppColors.primary,
        ),
        _buildStatCard(
          icon: Icons.calendar_today,
          title: l10n.todayAppointments,
          value: stats.todayAppointments.toString(),
          color: AppColors.secondary,
        ),
        _buildStatCard(
          icon: Icons.attach_money,
          title: l10n.todayRevenue,
          value: '\$${stats.todayRevenue.toStringAsFixed(0)}',
          color: AppColors.success,
        ),
        _buildStatCard(
          icon: Icons.pending_actions,
          title: 'Pending Appts', // Swapped from Pending Payments
          value: stats.pendingAppointments?.toString() ?? '0',
          color: AppColors.warning,
        ),
      ],
    );
  }

  Widget _buildStatCard({
    required IconData icon,
    required String title,
    required String value,
    required Color color,
  }) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(icon, color: color, size: 24),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  value,
                  style: const TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 12,
                    color: AppColors.textSecondary,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionTitle(BuildContext context, String title) {
    return Text(
      title,
      style: Theme.of(context).textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
    );
  }

  Widget _buildAppointmentsSection() {
    final appointmentState = ref.watch(appointmentNotifierProvider);

    return appointmentState.when(
      initial: () => const SizedBox.shrink(),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (message) => Text('Error loading appointments: $message'),
      loaded: (appointments, _, __, ___, ____) {
        if (appointments.isEmpty) {
          return Card(
            child: SizedBox(
              height: 100, // Compact empty state
              child: Center(
                child: Text(
                  AppLocalizations.of(context)!.noAppointmentsToday,
                  style: const TextStyle(color: AppColors.textSecondary),
                ),
              ),
            ),
          );
        }
        return Column(
          children: appointments.take(5).map((appt) => _buildAppointmentItem(appt)).toList(),
        );
      },
    );
  }

  Widget _buildAppointmentItem(AppointmentEntity appointment) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: AppColors.primary.withValues(alpha: 0.1),
          child: Text(
            appointment.patientName?.isNotEmpty == true ? appointment.patientName![0] : '?',
            style: const TextStyle(color: AppColors.primary),
          ),
        ),
        title: Text(appointment.patientName ?? 'Unknown'),
        subtitle: Text('${appointment.startTime} - ${appointment.procedureType ?? 'General'}'),
        trailing: Icon(Icons.chevron_right, color: AppColors.textDisabled),
        onTap: () {
          // TODO: Maybe navigate to detail
        },
      ),
    );
  }
}
