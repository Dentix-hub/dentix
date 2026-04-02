import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../../core/l10n/app_localizations.dart';
import '../../../../core/theme/app_colors.dart';
import '../controllers/appointment_notifier.dart';
import '../../domain/entities/appointment_entity.dart';

class AddAppointmentPage extends ConsumerStatefulWidget {
  const AddAppointmentPage({super.key});

  @override
  ConsumerState<AddAppointmentPage> createState() => _AddAppointmentPageState();
}

class _AddAppointmentPageState extends ConsumerState<AddAppointmentPage> {
  final _formKey = GlobalKey<FormState>();
  final _patientIdController = TextEditingController(); // TODO: Replace with Patient Picker
  final _notesController = TextEditingController();
  
  DateTime _selectedDate = DateTime.now();
  TimeOfDay _startTime = TimeOfDay.now();
  TimeOfDay _endTime = TimeOfDay.now().replacing(hour: TimeOfDay.now().hour + 1);
  String _procedureType = 'Checkup';
  
  bool _isLoading = false;

  final List<String> _procedures = [
    'Checkup',
    'Cleaning',
    'Filling',
    'Root Canal',
    'Extraction',
    'Whitening',
    'Crown',
    'Implant',
  ];

  @override
  void dispose() {
    _patientIdController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.newAppointment),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Patient ID Field (Temporary until Patient Picker)
              TextFormField(
                controller: _patientIdController,
                keyboardType: TextInputType.number,
                decoration: InputDecoration(
                  labelText: l10n.patientId, // Ensure this key exists
                  prefixIcon: const Icon(Icons.person),
                  border: const OutlineInputBorder(),
                  helperText: 'Enter Patient ID directly',
                ),
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return l10n.requiredField;
                  }
                  if (int.tryParse(value) == null) {
                    return l10n.invalidNumber;
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),

              // Date Picker
              InkWell(
                onTap: () => _selectDate(context),
                child: InputDecorator(
                  decoration: InputDecoration(
                    labelText: l10n.date,
                    prefixIcon: const Icon(Icons.calendar_today),
                    border: const OutlineInputBorder(),
                  ),
                  child: Text(
                    DateFormat('EEEE, MMM d, yyyy').format(_selectedDate),
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Time Pickers Row
              Row(
                children: [
                  Expanded(
                    child: InkWell(
                      onTap: () => _selectTime(context, true),
                      child: InputDecorator(
                        decoration: const InputDecoration(
                          labelText: 'Start Time', // TODO: Add l10n
                          prefixIcon: Icon(Icons.access_time),
                          border: OutlineInputBorder(),
                        ),
                        child: Text(_startTime.format(context)),
                      ),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: InkWell(
                      onTap: () => _selectTime(context, false),
                      child: InputDecorator(
                        decoration: const InputDecoration(
                          labelText: 'End Time', // TODO: Add l10n
                          prefixIcon: Icon(Icons.access_time_filled),
                          border: OutlineInputBorder(),
                        ),
                        child: Text(_endTime.format(context)),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Procedure Dropdown
              DropdownButtonFormField<String>(
                value: _procedureType,
                decoration: const InputDecoration(
                  labelText: 'Procedure', // TODO: Add l10n
                  prefixIcon: Icon(Icons.medical_services),
                  border: OutlineInputBorder(),
                ),
                items: _procedures.map((proc) {
                  return DropdownMenuItem(value: proc, child: Text(proc));
                }).toList(),
                onChanged: (value) {
                  if (value != null) setState(() => _procedureType = value);
                },
              ),
              const SizedBox(height: 16),

              // Notes Field
              TextFormField(
                controller: _notesController,
                maxLines: 3,
                decoration: InputDecoration(
                  labelText: l10n.description, // Reusing description key as Notes
                  prefixIcon: const Icon(Icons.notes),
                  border: const OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 32),

              // Submit Button
              SizedBox(
                height: 50,
                child: ElevatedButton(
                  onPressed: _isLoading ? null : _submit,
                  child: _isLoading
                      ? const CircularProgressIndicator()
                      : Text(l10n.newAppointment),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _selectDate(BuildContext context) async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _selectedDate,
      firstDate: DateTime.now(),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (picked != null) {
      setState(() => _selectedDate = picked);
    }
  }

  Future<void> _selectTime(BuildContext context, bool isStart) async {
    final picked = await showTimePicker(
      context: context,
      initialTime: isStart ? _startTime : _endTime,
    );
    if (picked != null) {
      setState(() {
        if (isStart) {
          _startTime = picked;
          // Auto-adjust end time if it's before start time
          if (_endTime.hour < _startTime.hour || 
              (_endTime.hour == _startTime.hour && _endTime.minute <= _startTime.minute)) {
             _endTime = TimeOfDay(hour: _startTime.hour + 1, minute: _startTime.minute);
          }
        } else {
          _endTime = picked;
        }
      });
    }
  }

  String _formatTimeOfDay(TimeOfDay time) {
    final now = DateTime.now();
    final dt = DateTime(now.year, now.month, now.day, time.hour, time.minute);
    return DateFormat('HH:mm').format(dt); // Backend expects HH:mm
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    final dateStr = DateFormat('yyyy-MM-dd').format(_selectedDate);
    
    // We are using a fixed doctor ID (1) for now as Mobile App context usually implies logged-in doctor
    // In a real app, we get this from AuthState
    const doctorId = 1; 

    final success = await ref.read(appointmentNotifierProvider.notifier).createAppointment(
      patientId: int.parse(_patientIdController.text),
      dentistId: doctorId,
      appointmentDate: dateStr,
      startTime: _formatTimeOfDay(_startTime),
      endTime: _formatTimeOfDay(_endTime),
      notes: _notesController.text,
      procedureType: _procedureType,
    );

    setState(() => _isLoading = false);

    if (success && mounted) {
      Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AppLocalizations.of(context)!.appointmentCreated ?? 'Appointment Created')),
      );
    }
  }
}
