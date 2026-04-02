import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/l10n/app_localizations.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../main.dart';
import '../../../auth/presentation/controllers/auth_notifier.dart';
import '../../../appointments/presentation/pages/appointment_calendar_page.dart';

class MorePage extends ConsumerWidget {
  const MorePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.more),
        automaticallyImplyLeading: false,
      ),
      body: ListView(
        children: [
          _buildMenuItem(
            context,
            icon: Icons.attach_money,
            title: l10n.financialOverview,
            color: Colors.green,
            onTap: () => context.push('/financial'),
          ),
          _buildMenuItem(
            context,
            icon: Icons.medication,
            title: l10n.prescriptions,
            color: Colors.orange,
            onTap: () => context.push('/prescriptions'),
          ),
          _buildMenuItem(
            context,
            icon: Icons.biotech,
            title: l10n.labOrders,
            color: Colors.blue,
            onTap: () => context.push('/lab-orders'),
          ),
          const Divider(),
          _buildMenuItem(
            context,
            icon: Icons.settings,
            title: l10n.settings,
            color: Colors.grey,
            onTap: () => context.push('/settings'),
          ),
          _buildMenuItem(
            context,
            icon: Icons.logout,
            title: l10n.logout,
            color: AppColors.error,
            onTap: () {
               // Show confirmation dialog
                showDialog(
                  context: context,
                  builder: (context) => AlertDialog(
                    title: Text(l10n.logout),
                    content: Text(l10n.confirmLogout),
                    actions: [
                      TextButton(
                        onPressed: () => Navigator.pop(context),
                        child: Text(l10n.cancel),
                      ),
                      TextButton(
                        onPressed: () {
                          Navigator.pop(context);
                          ref.read(authProvider.notifier).logout();
                        },
                        child: Text(
                          l10n.logout,
                          style: const TextStyle(color: AppColors.error),
                        ),
                      ),
                    ],
                  ),
                );
            },
          ),
        ],
      ),
    );
  }

  Widget _buildMenuItem(
    BuildContext context, {
    required IconData icon,
    required String title,
    required Color color,
    required VoidCallback onTap,
  }) {
    return ListTile(
      leading: Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Icon(icon, color: color),
      ),
      title: Text(title, style: const TextStyle(fontWeight: FontWeight.w500)),
      trailing: const Icon(Icons.chevron_right, size: 20),
      onTap: onTap,
    );
  }
}
