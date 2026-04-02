import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../../core/l10n/app_localizations.dart';
import '../../../../core/theme/app_colors.dart';
import '../../domain/entities/financial_transaction_entity.dart';
import '../controllers/financial_notifier.dart';
import 'record_payment_sheet.dart';

class FinancialOverviewPage extends ConsumerStatefulWidget {
  const FinancialOverviewPage({super.key});

  @override
  ConsumerState<FinancialOverviewPage> createState() =>
      _FinancialOverviewPageState();
}

class _FinancialOverviewPageState extends ConsumerState<FinancialOverviewPage> {
  final ScrollController _scrollController = ScrollController();
  String? _selectedMonth;

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
      ref.read(financialNotifierProvider.notifier).loadMoreTransactions();
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final state = ref.watch(financialNotifierProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.financialOverview),
        actions: [
          // Month filter button
          IconButton(
            icon: const Icon(Icons.calendar_month),
            onPressed: () => _showMonthPicker(context),
          ),
          // Clear filter button
          if (_selectedMonth != null)
            IconButton(
              icon: const Icon(Icons.clear),
              onPressed: () {
                setState(() => _selectedMonth = null);
                ref
                    .read(financialNotifierProvider.notifier)
                    .loadFinancialOverview();
              },
            ),
        ],
      ),
      body: state.when(
        initial: () {
          Future.microtask(() {
            ref
                .read(financialNotifierProvider.notifier)
                .loadFinancialOverview(month: _selectedMonth);
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
                      .read(financialNotifierProvider.notifier)
                      .loadFinancialOverview(month: _selectedMonth);
                },
                child: Text(l10n.retry),
              ),
            ],
          ),
        ),
        loaded: (transactions, totalRevenue, totalExpenses, netIncome,
            currentPage, totalPages, hasMore, selectedMonth) {
          return RefreshIndicator(
            onRefresh: () async {
              await ref
                  .read(financialNotifierProvider.notifier)
                  .loadFinancialOverview(month: _selectedMonth, refresh: true);
            },
            child: CustomScrollView(
              controller: _scrollController,
              slivers: [
                // Summary cards
                SliverToBoxAdapter(
                  child: _buildSummaryCards(
                    totalRevenue: totalRevenue,
                    totalExpenses: totalExpenses,
                    netIncome: netIncome,
                  ),
                ),
                // Transactions list
                SliverList(
                  delegate: SliverChildBuilderDelegate(
                    (context, index) {
                      if (index >= transactions.length) {
                        if (hasMore) {
                          return const Padding(
                            padding: EdgeInsets.all(16),
                            child: Center(child: CircularProgressIndicator()),
                          );
                        }
                        return const SizedBox.shrink();
                      }
                      return _buildTransactionCard(transactions[index]);
                    },
                    childCount: transactions.length + (hasMore ? 1 : 0),
                  ),
                ),
              ],
            ),
          );
        },
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _showRecordPaymentSheet(context),
        icon: const Icon(Icons.add),
        label: Text(l10n.recordPayment),
      ),
    );
  }

  Widget _buildSummaryCards({
    required int totalRevenue,
    required int totalExpenses,
    required double netIncome,
  }) {
    final l10n = AppLocalizations.of(context)!;
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: _buildSummaryCard(
                  title: l10n.revenue,
                  amount: '\$$totalRevenue',
                  color: AppColors.success,
                  icon: Icons.trending_up,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildSummaryCard(
                  title: l10n.expense,
                  amount: '\$$totalExpenses',
                  color: AppColors.error,
                  icon: Icons.trending_down,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          _buildSummaryCard(
            title: l10n.netIncome,
            amount: '\$${netIncome.toStringAsFixed(2)}',
            color: netIncome >= 0 ? AppColors.success : AppColors.error,
            icon: netIncome >= 0 ? Icons.account_balance : Icons.warning,
            fullWidth: true,
          ),
        ],
      ),
    );
  }

  Widget _buildSummaryCard({
    required String title,
    required String amount,
    required Color color,
    required IconData icon,
    bool fullWidth = false,
  }) {
    return Container(
      width: fullWidth ? double.infinity : null,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: color, size: 20),
              const SizedBox(width: 8),
              Text(
                title,
                style: TextStyle(
                  color: color,
                  fontWeight: FontWeight.w600,
                  fontSize: 14,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            amount,
            style: TextStyle(
              color: color,
              fontWeight: FontWeight.bold,
              fontSize: 20,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTransactionCard(FinancialTransactionEntity transaction) {
    final l10n = AppLocalizations.of(context)!;
    final isRevenue = transaction.isRevenue;
    final color = isRevenue ? AppColors.success : AppColors.error;

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: color.withOpacity(0.1),
          child: Icon(
            isRevenue ? Icons.arrow_upward : Icons.arrow_downward,
            color: color,
          ),
        ),
        title: Text(transaction.description ?? l10n.transactionNumber(transaction.id)),
        subtitle: Text(
          DateFormat('MMM d, yyyy').format(DateTime.parse(transaction.date)),
        ),
        trailing: Text(
          transaction.formattedAmount,
          style: TextStyle(
            color: color,
            fontWeight: FontWeight.bold,
            fontSize: 16,
          ),
        ),
      ),
    );
  }

  void _showMonthPicker(BuildContext context) {
    final now = DateTime.now();
    showModalBottomSheet(
      context: context,
      builder: (context) => SizedBox(
        height: 300,
        child: ListView.builder(
          itemCount: 12,
          itemBuilder: (context, index) {
            final month = DateTime(now.year, now.month - index, 1);
            final monthStr = DateFormat('yyyy-MM').format(month);
            final monthLabel = DateFormat('MMMM yyyy').format(month);

            return ListTile(
              title: Text(monthLabel),
              selected: _selectedMonth == monthStr,
              onTap: () {
                setState(() => _selectedMonth = monthStr);
                Navigator.pop(context);
                ref
                    .read(financialNotifierProvider.notifier)
                    .loadFinancialOverview(month: monthStr);
              },
            );
          },
        ),
      ),
    );
  }

  void _showRecordPaymentSheet(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => const RecordPaymentBottomSheet(),
    );
  }
}
