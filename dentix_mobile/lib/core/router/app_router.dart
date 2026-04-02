import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/l10n/app_localizations.dart';

import '../../features/auth/presentation/pages/login_page.dart';
import '../../features/auth/presentation/pages/splash_page.dart';
import '../../features/dashboard/presentation/pages/dashboard_page.dart';
import '../../features/patients/presentation/pages/patient_list_page.dart';
import '../../features/appointments/presentation/pages/appointment_calendar_page.dart';
import '../../features/settings/presentation/pages/settings_page.dart';
import '../../features/settings/presentation/pages/more_page.dart';
import '../../features/financial/presentation/pages/financial_overview_page.dart';
import '../../features/prescriptions/presentation/pages/prescriptions_list_page.dart';
import '../../features/lab_orders/presentation/pages/lab_orders_list_page.dart';
import '../../main.dart';

final _rootNavigatorKey = GlobalKey<NavigatorState>();
final _shellNavigatorKey = GlobalKey<NavigatorState>();

final goRouterProvider = Provider<GoRouter>((ref) {
  final authInterceptor = ref.watch(authInterceptorProvider);

  return GoRouter(
    navigatorKey: _rootNavigatorKey,
    debugLogDiagnostics: true,
    initialLocation: '/splash',
    redirect: (context, state) async {
      final isLoggedIn = await authInterceptor.isLoggedIn();
      final isAuthRoute = state.matchedLocation == '/login' ||
          state.matchedLocation == '/splash';

      if (!isLoggedIn && !isAuthRoute) {
        return '/login';
      }

      if (isLoggedIn && isAuthRoute) {
        return '/dashboard';
      }

      return null;
    },
    routes: [
      GoRoute(
        path: '/splash',
        builder: (context, state) => const SplashPage(),
      ),
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginPage(),
      ),
      GoRoute(
        path: '/financial',
        builder: (context, state) => const FinancialOverviewPage(),
      ),
      GoRoute(
        path: '/prescriptions',
        builder: (context, state) => const PrescriptionsListPage(),
      ),
      GoRoute(
        path: '/lab-orders',
        builder: (context, state) => const LabOrdersListPage(),
      ),
      GoRoute(
        path: '/settings',
        builder: (context, state) => const SettingsPage(),
      ),
      ShellRoute(
        navigatorKey: _shellNavigatorKey,
        builder: (context, state, child) => ScaffoldWithNavBar(child: child),
        routes: [
          GoRoute(
            path: '/dashboard',
            builder: (context, state) => const DashboardPage(),
          ),
          GoRoute(
            path: '/patients',
            builder: (context, state) => const PatientListPage(),
          ),
          GoRoute(
            path: '/appointments',
            builder: (context, state) => const AppointmentCalendarPage(),
          ),
          GoRoute(
            path: '/more',
            builder: (context, state) => const MorePage(),
          ),
        ],
      ),
    ],
  );
});

class ScaffoldWithNavBar extends StatelessWidget {
  final Widget child;

  const ScaffoldWithNavBar({
    super.key,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: child,
      bottomNavigationBar: NavigationBar(
        onDestinationSelected: (index) {
          switch (index) {
            case 0:
              context.go('/dashboard');
              break;
            case 1:
              context.go('/patients');
              break;
            case 2:
              context.go('/appointments');
              break;
            case 3:
              context.go('/more');
              break;
          }
        },
        selectedIndex: _calculateSelectedIndex(context),
        destinations: [
          NavigationDestination(
            icon: const Icon(Icons.dashboard_outlined),
            selectedIcon: const Icon(Icons.dashboard),
            label: AppLocalizations.of(context)!.dashboard,
          ),
          NavigationDestination(
            icon: const Icon(Icons.people_outline),
            selectedIcon: const Icon(Icons.people),
            label: AppLocalizations.of(context)!.patients,
          ),
          NavigationDestination(
            icon: const Icon(Icons.calendar_today_outlined),
            selectedIcon: const Icon(Icons.calendar_today),
            label: AppLocalizations.of(context)!.appointments,
          ),
          NavigationDestination(
            icon: const Icon(Icons.menu),
            selectedIcon: const Icon(Icons.menu_open),
            label: AppLocalizations.of(context)!.more,
          ), // TODO: Ensure 'more' key exists in localization or use literal
        ],
      ),
    );
  }

  int _calculateSelectedIndex(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    if (location.startsWith('/dashboard')) return 0;
    if (location.startsWith('/patients')) return 1;
    if (location.startsWith('/appointments')) return 2;
    if (location.startsWith('/more')) return 3;
    return 0; 
  }
}
