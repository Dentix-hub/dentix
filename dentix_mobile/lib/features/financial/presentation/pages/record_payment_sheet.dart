import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../../core/l10n/app_localizations.dart';
import '../../../../core/theme/app_colors.dart';
import '../controllers/financial_notifier.dart';

class RecordPaymentBottomSheet extends ConsumerStatefulWidget {
  const RecordPaymentBottomSheet({super.key});

  @override
  ConsumerState<RecordPaymentBottomSheet> createState() =>
      _RecordPaymentBottomSheetState();
}

class _RecordPaymentBottomSheetState
    extends ConsumerState<RecordPaymentBottomSheet> {
  final _formKey = GlobalKey<FormState>();
  final _amountController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _patientIdController = TextEditingController();
  
  DateTime _selectedDate = DateTime.now();
  bool _isRevenue = true;
  bool _isLoading = false;

  @override
  void dispose() {
    _amountController.dispose();
    _descriptionController.dispose();
    _patientIdController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: Container(
        padding: const EdgeInsets.all(24),
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Handle bar
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: AppColors.divider,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 24),
              
              // Title
              Text(
                l10n.recordPayment,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              
              // Transaction Type Toggle
              SegmentedButton<bool>(
                segments: [
                  ButtonSegment(
                    value: true,
                    label: Text(l10n.revenue),
                    icon: const Icon(Icons.arrow_upward),
                  ),
                  ButtonSegment(
                    value: false,
                    label: Text(l10n.expense),
                    icon: const Icon(Icons.arrow_downward),
                  ),
                ],
                selected: {_isRevenue},
                onSelectionChanged: (value) {
                  setState(() => _isRevenue = value.first);
                },
              ),
              const SizedBox(height: 16),
              
              // Amount Field
              TextFormField(
                controller: _amountController,
                keyboardType: TextInputType.number,
                decoration: InputDecoration(
                  labelText: l10n.amount,
                  prefixIcon: const Icon(Icons.attach_money),
                  border: const OutlineInputBorder(),
                ),
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return l10n.requiredField;
                  }
                  final amount = double.tryParse(value);
                  if (amount == null || amount <= 0) {
                    return l10n.invalidAmount;
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
                    DateFormat('MMM d, yyyy').format(_selectedDate),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              
              // Patient ID Field
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
              
              // Description Field
              TextFormField(
                controller: _descriptionController,
                maxLines: 2,
                decoration: InputDecoration(
                  labelText: l10n.description,
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
                      : Text(l10n.recordPayment),
                ),
              ),
              const SizedBox(height: 16),
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
      firstDate: DateTime(2020),
      lastDate: DateTime.now(),
    );
    if (picked != null) {
      setState(() => _selectedDate = picked);
    }
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    final amount = double.parse(_amountController.text);
    final finalAmount = _isRevenue ? amount : -amount;
    
    final success = await ref.read(financialNotifierProvider.notifier).recordPayment(
      patientId: int.parse(_patientIdController.text),
      amount: finalAmount,
      date: DateFormat('yyyy-MM-dd').format(_selectedDate),
      description: _descriptionController.text.isEmpty
          ? null
          : _descriptionController.text,
    );

    setState(() => _isLoading = false);

    if (success && mounted) {
      Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AppLocalizations.of(context)!.paymentRecorded)),
      );
    }
  }
}
