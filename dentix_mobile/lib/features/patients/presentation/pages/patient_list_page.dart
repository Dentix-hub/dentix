import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/l10n/app_localizations.dart';
import '../../../../core/theme/app_colors.dart';
import '../../domain/entities/patient_entity.dart';
import '../controllers/patient_list_notifier.dart';
import 'patient_detail_page.dart';
import 'add_patient_page.dart';
import '../../../../shared/widgets/empty_state.dart';
import '../../../../shared/widgets/error_retry_widget.dart';

class PatientListPage extends ConsumerStatefulWidget {
  const PatientListPage({super.key});

  @override
  ConsumerState<PatientListPage> createState() => _PatientListPageState();
}

class _PatientListPageState extends ConsumerState<PatientListPage> {
  final ScrollController _scrollController = ScrollController();
  Timer? _debounceTimer;
  static const Duration _debounceDelay = Duration(milliseconds: 300);

  @override
  void initState() {
    super.initState();
    Future.microtask(() {
      ref.read(patientListNotifierProvider.notifier).loadPatients();
    });
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _debounceTimer?.cancel();
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent - 200) {
      ref.read(patientListNotifierProvider.notifier).loadMorePatients();
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(patientListNotifierProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(AppLocalizations.of(context)!.patients),
        automaticallyImplyLeading: false,
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Search Bar
            Padding(
              padding: const EdgeInsets.all(16),
              child: TextField(
                onChanged: (value) {
                  _debounceTimer?.cancel();
                  _debounceTimer = Timer(_debounceDelay, () {
                    ref.read(patientListNotifierProvider.notifier).searchPatients(value);
                  });
                },
                decoration: InputDecoration(
                  hintText: AppLocalizations.of(context)!.searchPatients,
                  prefixIcon: const Icon(Icons.search),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
            ),
            
            // Patient List
            Expanded(
              child: state.when(
                initial: () => const SizedBox.shrink(),
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (message) => _buildErrorView(message),
                loaded: (patients, totalPages, currentPage, hasMore, searchQuery) {
                  if (patients.isEmpty) {
                    return _buildEmptyState();
                  }
                  return _buildPatientList(patients, hasMore);
                },
              ),
            ),
          ],
        ),
      ),
      floatingActionButton: ElevatedButton.icon(
        onPressed: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => const AddPatientPage(),
            ),
          );
        },
        icon: const Icon(Icons.add),
        label: Text(AppLocalizations.of(context)!.addPatient),
      ),
    );
  }

  Widget _buildErrorView(String message) {
    return ErrorRetryWidget(
      message: message,
      onRetry: () {
        ref.read(patientListNotifierProvider.notifier).loadPatients(refresh: true);
      },
    );
  }

  Widget _buildPatientList(List patients, bool hasMore) {
    return ListView.builder(
      controller: _scrollController,
      itemCount: patients.length + (hasMore ? 1 : 0),
      itemBuilder: (context, index) {
        if (index >= patients.length) {
          return const Padding(
            padding: EdgeInsets.all(16),
            child: Center(child: CircularProgressIndicator()),
          );
        }
        
        final patient = patients[index];
        return _buildPatientCard(patient);
      },
    );
  }

  Widget _buildPatientCard(PatientEntity patient) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: AppColors.primary,
          child: Text(
            patient.fullName.isNotEmpty ? patient.fullName[0].toUpperCase() : '?',
            style: const TextStyle(color: Colors.white),
          ),
        ),
        title: Text(patient.fullName),
        subtitle: Text(patient.phone ?? patient.email ?? ''),
        trailing: const Icon(Icons.chevron_right),
        onTap: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => PatientDetailPage(patient: patient),
            ),
          );
        },
      ),
    );
  }

  Widget _buildEmptyState() {
    return EmptyState(
      icon: Icons.people_outline,
      message: AppLocalizations.of(context)!.noPatientsFound,
      subtitle: AppLocalizations.of(context)!.addFirstPatient,
    );
  }
}
