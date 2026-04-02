import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/l10n/app_localizations.dart';
import 'package:intl/intl.dart';

import '../../../../core/theme/app_colors.dart';
import '../controllers/appointment_notifier.dart';
import '../../domain/entities/appointment_entity.dart';
import '../../../../shared/widgets/empty_state.dart';
import '../../../../shared/widgets/error_retry_widget.dart';
import 'add_appointment_page.dart';

class AppointmentCalendarPage extends ConsumerStatefulWidget {
  const AppointmentCalendarPage({super.key});

  @override
  ConsumerState<AppointmentCalendarPage> createState() => _AppointmentCalendarPageState();
}

class _AppointmentCalendarPageState extends ConsumerState<AppointmentCalendarPage> {
  DateTime _selectedDate = DateTime.now();

  @override
  void initState() {
    super.initState();
    Future.microtask(() {
      _loadAppointmentsForSelectedDate();
    });
  }

  void _loadAppointmentsForSelectedDate() {
    final formattedDate = DateFormat('yyyy-MM-dd').format(_selectedDate);
    ref.read(appointmentNotifierProvider.notifier).selectDate(formattedDate);
  }

  void _goToToday() {
    setState(() {
      _selectedDate = DateTime.now();
    });
    _loadAppointmentsForSelectedDate();
  }

  void _previousDay() {
    setState(() {
      _selectedDate = _selectedDate.subtract(const Duration(days: 1));
    });
    _loadAppointmentsForSelectedDate();
  }

  void _nextDay() {
    setState(() {
      _selectedDate = _selectedDate.add(const Duration(days: 1));
    });
    _loadAppointmentsForSelectedDate();
  }

  Future<void> _selectDate(BuildContext context) async {
    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate: _selectedDate,
      firstDate: DateTime(2020),
      lastDate: DateTime(2030),
    );
    if (picked != null && picked != _selectedDate) {
      setState(() {
        _selectedDate = picked;
      });
      _loadAppointmentsForSelectedDate();
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(appointmentNotifierProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(AppLocalizations.of(context)!.appointments),
        automaticallyImplyLeading: false,
        actions: [
          IconButton(
            icon: const Icon(Icons.today),
            onPressed: _goToToday,
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            _buildDateSelector(),
            const Divider(),
            Expanded(
              child: state.when(
                initial: () => const SizedBox.shrink(),
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (message) => _buildErrorView(message),
                loaded: (appointments, totalPages, currentPage, hasMore, selectedDate) {
                  if (appointments.isEmpty) {
                    return _buildEmptyState();
                  }
                  return _buildAppointmentsList(appointments, hasMore);
                },
              ),
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () async {
          await Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => const AddAppointmentPage(),
            ),
          );
          _loadAppointmentsForSelectedDate();
        },
        icon: const Icon(Icons.add),
        label: Text(AppLocalizations.of(context)!.newAppointment),
      ),
    );
  }

  Widget _buildDateSelector() {
    final dateStr = DateFormat('EEEE, MMMM d, yyyy').format(_selectedDate);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          IconButton(
            icon: const Icon(Icons.chevron_left),
            onPressed: _previousDay,
          ),
          Expanded(
            child: GestureDetector(
              onTap: () => _selectDate(context),
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 8),
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  dateStr,
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 16),
                ),
              ),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.chevron_right),
            onPressed: _nextDay,
          ),
        ],
      ),
    );
  }

  Widget _buildErrorView(String message) {
    return ErrorRetryWidget(
      message: message,
      onRetry: _loadAppointmentsForSelectedDate,
    );
  }

  Widget _buildAppointmentsList(List<AppointmentEntity> appointments, bool hasMore) {
    return RefreshIndicator(
      onRefresh: () async => _loadAppointmentsForSelectedDate(),
      child: ListView.builder(
        itemCount: appointments.length + (hasMore ? 1 : 0),
        itemBuilder: (context, index) {
          if (index >= appointments.length) {
            ref.read(appointmentNotifierProvider.notifier).loadMoreAppointments();
            return const Padding(
              padding: EdgeInsets.all(16),
              child: Center(child: CircularProgressIndicator()),
            );
          }
          final appointment = appointments[index];
          return Dismissible(
            key: Key('appointment_${appointment.id}'),
            background: Container(
              color: AppColors.error,
              alignment: Alignment.centerRight,
              padding: const EdgeInsets.only(right: 20),
              child: const Icon(Icons.cancel, color: Colors.white),
            ),
            direction: DismissDirection.endToStart,
            confirmDismiss: (direction) async {
               return await showDialog(
                 context: context,
                 builder: (BuildContext context) {
                   return AlertDialog(
                     title: Text(AppLocalizations.of(context)!.cancel), // Reusing existing keys or generic
                     content: const Text("Are you sure you want to cancel this appointment?"),
                     actions: <Widget>[
                       TextButton(onPressed: () => Navigator.of(context).pop(false), child: Text(AppLocalizations.of(context)!.cancel)),
                       TextButton(
                         onPressed: () {
                           Navigator.of(context).pop(true);
                           // Actual delete/cancel call
                           ref.read(appointmentNotifierProvider.notifier).cancelAppointment(appointment.id);
                         },
                         child: const Text("Yes"),
                       ),
                     ],
                   );
                 },
               );
             },
            child: _buildAppointmentCard(appointment)
          );
        },
      ),
    );
  }

  Widget _buildAppointmentCard(AppointmentEntity appointment) {
    Color statusColor = switch (appointment.status.toLowerCase()) {
      'completed' => AppColors.success,
      'cancelled' => AppColors.error,
      _ => AppColors.primary,
    };
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: ListTile(
        leading: Container(width: 4, height: 40, decoration: BoxDecoration(color: statusColor, borderRadius: BorderRadius.circular(2))),
        title: Text(appointment.patientName ?? 'Unknown', style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text('${appointment.startTime} - ${appointment.procedureType ?? 'General'}', style: TextStyle(color: AppColors.textSecondary)),
        trailing: Chip(
          label: Text(appointment.status, style: const TextStyle(fontSize: 12, color: Colors.white)),
          backgroundColor: statusColor,
        ),
        onTap: () {
          // TODO: Open detail or edit logic
        },
        onLongPress: () {
             // Quick complete action
               showDialog(
                 context: context,
                 builder: (BuildContext context) {
                   return AlertDialog(
                     title: const Text("Complete Appointment?"),
                     content: const Text("Mark this appointment as completed?"),
                     actions: <Widget>[
                       TextButton(onPressed: () => Navigator.of(context).pop(), child: Text(AppLocalizations.of(context)!.cancel)),
                       TextButton(
                         onPressed: () {
                           Navigator.of(context).pop();
                           ref.read(appointmentNotifierProvider.notifier).completeAppointment(appointment.id);
                         },
                         child: const Text("Yes")
                       ),
                     ],
                   );
                 },
               );
        },
      ),
    );
  }

  Widget _buildEmptyState() {
    return EmptyState(
      icon: Icons.event_note_outlined,
      message: AppLocalizations.of(context)!.noAppointments,
      subtitle: AppLocalizations.of(context)!.tapToAddAppointment,
    );
  }
}
