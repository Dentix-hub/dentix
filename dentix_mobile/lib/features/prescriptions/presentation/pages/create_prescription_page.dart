import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/l10n/app_localizations.dart';
import '../../../../core/theme/app_colors.dart';
import '../controllers/prescription_notifier.dart';

class CreatePrescriptionPage extends ConsumerStatefulWidget {
  const CreatePrescriptionPage({super.key});

  @override
  ConsumerState<CreatePrescriptionPage> createState() =>
      _CreatePrescriptionPageState();
}

class _CreatePrescriptionPageState
    extends ConsumerState<CreatePrescriptionPage> {
  final _formKey = GlobalKey<FormState>();
  final _patientIdController = TextEditingController();
  final _notesController = TextEditingController();
  
  final List<Map<String, dynamic>> _medications = [];
  bool _isLoading = false;

  @override
  void dispose() {
    _patientIdController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  void _addMedication() {
    setState(() {
      _medications.add({
        'medication_id': 0,
        'dosage': '',
        'frequency': '',
        'duration': '',
        'instructions': '',
      });
    });
  }

  void _removeMedication(int index) {
    setState(() {
      _medications.removeAt(index);
    });
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.createPrescription),
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Patient ID
            TextFormField(
              controller: _patientIdController,
              keyboardType: TextInputType.number,
              decoration: InputDecoration(
                labelText: l10n.patientId,
                prefixIcon: const Icon(Icons.person),
                border: const OutlineInputBorder(),
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
            
            // Medications Section
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  l10n.medications,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                TextButton.icon(
                  onPressed: _addMedication,
                  icon: const Icon(Icons.add),
                  label: Text(l10n.addMedication),
                ),
              ],
            ),
            const SizedBox(height: 8),
            
            // Medication List
            ..._medications.asMap().entries.map((entry) {
              final index = entry.key;
              final medication = entry.value;
              return _buildMedicationCard(index, medication);
            }),
            
            if (_medications.isEmpty)
              Center(
                child: Padding(
                  padding: const EdgeInsets.all(32),
                  child: Text(
                    l10n.noMedicationsAdded,
                    style: TextStyle(color: AppColors.textSecondary),
                  ),
                ),
              ),
            
            const SizedBox(height: 16),
            
            // Notes
            TextFormField(
              controller: _notesController,
              maxLines: 3,
              decoration: InputDecoration(
                labelText: l10n.notes,
                prefixIcon: const Icon(Icons.notes),
                border: const OutlineInputBorder(),
                alignLabelWithHint: true,
              ),
            ),
            const SizedBox(height: 24),
            
            // Submit Button
            SizedBox(
              height: 50,
              child: ElevatedButton(
                onPressed: _isLoading ? null : _submit,
                child: _isLoading
                    ? const CircularProgressIndicator()
                    : Text(l10n.createPrescription),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMedicationCard(int index, Map<String, dynamic> medication) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  '${AppLocalizations.of(context)!.medication} #${index + 1}',
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                IconButton(
                  onPressed: () => _removeMedication(index),
                  icon: const Icon(Icons.delete, color: AppColors.error),
                ),
              ],
            ),
            const SizedBox(height: 8),
            TextFormField(
              initialValue: medication['medication_id']?.toString(),
              keyboardType: TextInputType.number,
              decoration: InputDecoration(
                labelText: AppLocalizations.of(context)!.medicationId,
                border: const OutlineInputBorder(),
              ),
              onChanged: (value) {
                medication['medication_id'] = int.tryParse(value) ?? 0;
              },
              validator: (value) {
                if (value == null || value.isEmpty) {
                  return AppLocalizations.of(context)!.requiredField;
                }
                return null;
              },
            ),
            const SizedBox(height: 12),
            TextFormField(
              initialValue: medication['dosage'],
              decoration: InputDecoration(
                labelText: AppLocalizations.of(context)!.dosage,
                border: const OutlineInputBorder(),
              ),
              onChanged: (value) => medication['dosage'] = value,
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    initialValue: medication['frequency'],
                    decoration: InputDecoration(
                      labelText: AppLocalizations.of(context)!.frequency,
                      border: const OutlineInputBorder(),
                    ),
                    onChanged: (value) => medication['frequency'] = value,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextFormField(
                    initialValue: medication['duration'],
                    decoration: InputDecoration(
                      labelText: AppLocalizations.of(context)!.duration,
                      border: const OutlineInputBorder(),
                    ),
                    onChanged: (value) => medication['duration'] = value,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_medications.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(AppLocalizations.of(context)!.addAtLeastOneMedication),
        ),
      );
      return;
    }

    setState(() => _isLoading = true);

    final success = await ref
        .read(prescriptionNotifierProvider.notifier)
        .createPrescription(
          patientId: int.parse(_patientIdController.text),
          medications: _medications,
          notes: _notesController.text.isEmpty ? null : _notesController.text,
        );

    setState(() => _isLoading = false);

    if (success && mounted) {
      Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(AppLocalizations.of(context)!.prescriptionCreated),
        ),
      );
    }
  }
}
