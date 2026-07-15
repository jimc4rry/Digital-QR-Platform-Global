import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../models/order.dart';
import '../models/staff_user.dart';
import '../services/api_client.dart';
import '../services/auth_service.dart';
import '../services/staff_repository.dart';
import '../widgets/status_badge.dart';
import '../widgets/empty_state.dart';
import 'order_detail_screen.dart';
import 'product_list_screen.dart';
import 'owner_tools_screen.dart';
import 'login_screen.dart';

class OrderListScreen extends StatefulWidget {
  const OrderListScreen({super.key});

  @override
  State<OrderListScreen> createState() => _OrderListScreenState();
}

class _OrderListScreenState extends State<OrderListScreen> {
  late final StaffRepository _repository;
  Future<List<OrderSummary>>? _ordersFuture;
  StaffUser? _me;
  String? _statusFilter;
  final _currencyFormat = NumberFormat.currency(locale: 'el_GR', symbol: '€');

  @override
  void initState() {
    super.initState();
    final authService = context.read<AuthService>();
    _repository = StaffRepository(ApiClient(authService));
    _loadMe();
    _loadOrders();
  }

  Future<void> _loadMe() async {
    try {
      final me = await _repository.getMe();
      if (mounted) setState(() => _me = me);
    } catch (_) {
      // Non-fatal - the app still works, just without the restaurant name in the app bar.
    }
  }

  void _loadOrders() {
    final future = _repository.getOrders(status: _statusFilter);
    setState(() {
      _ordersFuture = future;
    });
  }

  Future<void> _logout() async {
    await context.read<AuthService>().logout();
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const LoginScreen()),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: Text(_me?.restaurantName ?? 'Orders'),
        actions: [
          if (_me != null)
            IconButton(
              icon: const Icon(Icons.restaurant_menu_rounded),
              tooltip: 'Products',
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => ProductListScreen(canManageMenu: _me!.canManageMenu),
                ),
              ),
            ),
          if (_me != null && !_me!.isEmployee)
            IconButton(
              icon: const Icon(Icons.admin_panel_settings_rounded),
              tooltip: 'Management',
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => OwnerToolsScreen(me: _me!, repository: _repository),
                ),
              ),
            ),
          IconButton(
            icon: const Icon(Icons.logout_rounded),
            tooltip: 'Log Out',
            onPressed: _logout,
          ),
          const SizedBox(width: 4),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(52),
          child: Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(
                children: [
                  _FilterChip(label: 'All', selected: _statusFilter == null, onTap: () {
                    _statusFilter = null;
                    _loadOrders();
                  }),
                  for (final choice in orderStatusChoices)
                    Padding(
                      padding: const EdgeInsets.only(left: 8),
                      child: _FilterChip(
                        label: choice['label']!,
                        color: statusColor(choice['value']!),
                        selected: _statusFilter == choice['value'],
                        onTap: () {
                          _statusFilter = choice['value'];
                          _loadOrders();
                        },
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: () async => _loadOrders(),
        child: _ordersFuture == null
            ? const Center(child: CircularProgressIndicator())
            : AsyncListView<List<OrderSummary>>(
                future: _ordersFuture!,
                onRetry: _loadOrders,
                builder: (context, orders) {
                  if (orders.isEmpty) {
                    return ListView(
                      children: const [
                        SizedBox(height: 80),
                        EmptyState(icon: Icons.receipt_long_rounded, message: 'No orders yet'),
                      ],
                    );
                  }
                  return ListView.builder(
                    padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
                    itemCount: orders.length,
                    itemBuilder: (context, index) {
                      final order = orders[index];
                      return _OrderCard(
                        order: order,
                        currencyFormat: _currencyFormat,
                        onTap: () async {
                          await Navigator.of(context).push(
                            MaterialPageRoute(builder: (_) => OrderDetailScreen(orderId: order.id)),
                          );
                          _loadOrders();
                        },
                      );
                    },
                  );
                },
              ),
      ),
      backgroundColor: scheme.surface,
    );
  }
}

class _OrderCard extends StatelessWidget {
  final OrderSummary order;
  final NumberFormat currencyFormat;
  final VoidCallback onTap;

  const _OrderCard({required this.order, required this.currencyFormat, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final color = statusColor(order.status);
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(color: color.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(12)),
                child: Icon(Icons.receipt_rounded, color: color, size: 22),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('#${order.orderNumber}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
                    const SizedBox(height: 3),
                    Text(
                      '${order.tableNumber.isNotEmpty ? "${order.tableTypeDisplay} ${order.tableNumber} · " : ""}'
                      '${DateFormat('dd/MM HH:mm').format(order.createdAt.toLocal())}',
                      style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant, fontSize: 12.5),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(currencyFormat.format(order.total), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
                  const SizedBox(height: 6),
                  StatusBadge(status: order.status, label: order.statusDisplay),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _FilterChip extends StatelessWidget {
  final String label;
  final bool selected;
  final Color? color;
  final VoidCallback onTap;
  const _FilterChip({required this.label, required this.selected, required this.onTap, this.color});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final activeColor = color ?? scheme.primary;
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 9),
        decoration: BoxDecoration(
          color: selected ? activeColor : (Theme.of(context).brightness == Brightness.dark
              ? scheme.surfaceContainerHigh
              : const Color(0xFFEFEFF6)),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: selected ? Colors.white : scheme.onSurfaceVariant,
            fontWeight: FontWeight.w600,
            fontSize: 13,
          ),
        ),
      ),
    );
  }
}
