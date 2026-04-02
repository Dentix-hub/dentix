import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../../core/l10n/app_localizations.dart';
import '../../../../core/theme/app_colors.dart';
import '../controllers/lab_order_notifier.dart';

class CreateLabOrderPage extends ConsumerStatefulWidget {
  const CreateLabOrderPage({super.key});

  @override
  ConsumerState<CreateLabOrderPage> createState() =>
      _CreateLabOrderPageState();
}

class _CreateLabOrderPageState extends ConsumerState<CreateLabOrderPage> {
  final _formKey = GlobalKey<FormState>();
  final _patientIdController = TextEditingController();
  final _labNameController = TextEditingController();
  final _notesController = TextEditingController();

  DateTime _selectedDate = DateTime.now().add(const Duration(days: 7));
  final List<Map<String, dynamic>> _workItems = [];
  bool _isLoading = false;

  @override
  void dispose() {
    _patientIdController.dispose();
    _labNameController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  void _addWorkItem() {
    setState(() {
      _workItems.add({
        'work_type': '',
        'quantity': 1,
        'description': '',
        'shade': '',
        'material': '',
      });
    });
  }

  void _removeWorkItem(int index) {
    setState(() {
      _workItems.removeAt(index);
    });
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.createLabOrder),
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

            // Lab Name
            TextFormField(
              controller: _labNameController,
              decoration: InputDecoration(
                labelText: l10n.labName,
                prefixIcon: const Icon(Icons.business),
                border: const OutlineInputBorder(),
              ),
              validator: (value) {
                if (value == null || value.isEmpty) {
                  return l10n.requiredField;
                }
                return null;
              },
            ),
            const SizedBox(height: 16),

            // Due Date
            InkWell(
              onTap: () => _selectDate(context),
              child: InputDecorator(
                decoration: InputDecoration(
                  labelText: l10n.dueDate,
                  prefixIcon: const Icon(Icons.calendar_today),
                  border: const OutlineInputBorder(),
                ),
                child: Text(
                  DateFormat('MMM d, yyyy').format(_selectedDate),
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Work Items Section
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  l10n.workItems,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                TextButton.icon(
                  onPressed: _addWorkItem,
                  icon: const Icon(Icons.add),
                  label: Text(l10n.addWorkItem),
                ),
              ],
            ),
            const SizedBox(height: 8),

            // Work Items List
            ..._workItems.asMap().entries.map((entry) {
              final index = entry.key;
              final item = entry.value;
              return _buildWorkItemCard(index, item);
            }),

            if (_workItems.isEmpty)
              Center(
                child: Padding(
                  padding: const EdgeInsets.all(32),
                  child: Text(
                    l10n.noWorkItemsAdded,
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
                    : Text(l10n.createLabOrder),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildWorkItemCard(int index, Map<String, dynamic> item) {
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
                  '${AppLocalizations.of(context)!.workItem} #${index + 1}',
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                IconButton(
                  onPressed: () => _removeWorkItem(index),
                  icon: const Icon(Icons.delete, color: AppColors.error),
                ),
              ],
            ),
            const SizedBox(height: 8),
            TextFormField(
              initialValue: item['work_type'],
              decoration: InputDecoration(
                labelText: AppLocalizations.of(context)!.workType,
                border: const OutlineInputBorder(),
              ),
              onChanged: (value) => item['work_type'] = value,
              validator: (value) {
                if (value == null || value.isEmpty) {
                  return AppLocalizations.of(context)!.requiredField;
                }
                return null;
              },
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  flex: 2,
                  child: TextFormField(
                    initialValue: item['quantity'].toString(),
                    keyboardType: TextInputType.number,
                    decoration: InputDecoration(
                      labelText: AppLocalizations.of(context)!.quantity,
                      border: const OutlineInputBorder(),
                    ),
                    onChanged: (value) =>
                        item['quantity'] = int.tryParse(value) ?? 1,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  flex: 3,
                  child: TextFormField(
                    initialValue: item['material'],
                    decoration: InputDecoration(
                      labelText: AppLocalizations.of(context)!.material,
                      border: const OutlineInputBorder(),
                    ),
                    onChanged: (value) => item['material'] = value,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            TextFormField(
              initialValue: item['shade'],
              decoration: InputDecoration(
                labelText: AppLocalizations.of(context)!.shade,
                border: const OutlineInputBorder(),
              ),
              onChanged: (value) => item['shade'] = value,
            ),
          ],
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

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_workItems.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(AppLocalizations.of(context)!.addAtLeastOneWorkItem),
        ),
      );
      return;
    }

    setState(() => _isLoading = true);

    final success = await ref.read(labOrderNotifierProvider.notifier).createLabOrder(
      patientId: int.parse(_patientIdController.text),
      labName: _labNameController.text,
      dueDate: DateFormat('yyyy-MM-dd').format(_selectedDate),
      items: _workItems,
      notes: _notesController.text.isEmpty ? null : _notesController.text,
    );

    setState(() => _isLoading = false);

    if (success && mounted) {
      Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(AppLocalizations.of(context)!.labOrderCreated),
        ),
      );
    }
  }
}
