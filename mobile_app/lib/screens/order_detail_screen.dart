import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../models/order.dart';
import '../services/api_client.dart';
import '../services/auth_service.dart';
import '../services/staff_repository.dart';
import '../widgets/empty_state.dart';
import '../widgets/status_badge.dart';

class OrderDetailScreen extends StatefulWidget {
  final int orderId;
  const OrderDetailScreen({super.key, required this.orderId});

  @override
  State<OrderDetailScreen> createState() => _OrderDetailScreenState();
}

class _OrderDetailScreenState extends State<OrderDetailScreen> {
  late final StaffRepository _repository;
  late Future<OrderDetail> _orderFuture;
  bool _updating = false;
  final _currencyFormat = NumberFormat.currency(locale: 'el_GR', symbol: '€');

  @override
  void initState() {
    super.initState();
    _repository = StaffRepository(ApiClient(context.read<AuthService>()));
    _load();
  }

  void _load() {
    final future = _repository.getOrderDetail(widget.orderId);
    setState(() {
      _orderFuture = future;
    });
  }

  Future<void> _updateStatus(String newStatus) async {
    setState(() => _updating = true);
    try {
      await _repository.updateOrderStatus(widget.orderId, newStatus);
      _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e is ApiException ? e.message : 'Update failed.')),
        );
      }
    } finally {
      if (mounted) setState(() => _updating = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Order Details')),
      body: AsyncListView<OrderDetail>(
        future: _orderFuture,
        onRetry: _load,
        builder: (context, order) {
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('#${order.orderNumber}', style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
                      StatusBadge(status: order.status, label: order.statusDisplay),
                    ],
                  ),
                ),
              ),
              if (order.tableNumber.isNotEmpty ||
                  order.customerName.isNotEmpty ||
                  order.customerPhone.isNotEmpty ||
                  order.customerNotes.isNotEmpty)
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (order.tableNumber.isNotEmpty)
                          _InfoRow(
                            order.isSunbed ? Icons.beach_access_rounded : Icons.table_bar_rounded,
                            order.tableTypeDisplay,
                            order.tableNumber,
                          ),
                        if (order.customerName.isNotEmpty)
                          _InfoRow(Icons.person_outline_rounded, 'Customer', order.customerName),
                        if (order.customerPhone.isNotEmpty)
                          _InfoRow(Icons.call_outlined, 'Phone', order.customerPhone),
                        if (order.customerNotes.isNotEmpty)
                          _InfoRow(Icons.sticky_note_2_outlined, 'Notes', order.customerNotes),
                        _InfoRow(Icons.schedule_rounded, 'Date',
                            DateFormat('dd/MM/yyyy HH:mm').format(order.createdAt.toLocal()), isLast: true),
                      ],
                    ),
                  ),
                ),
              Card(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Products', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
                      const SizedBox(height: 4),
                      ...order.items.map((item) => Padding(
                            padding: const EdgeInsets.symmetric(vertical: 8),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                  decoration: BoxDecoration(
                                    color: Theme.of(context).colorScheme.primaryContainer,
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: Text('${item.quantity}x',
                                      style: TextStyle(
                                          fontWeight: FontWeight.w700,
                                          fontSize: 12,
                                          color: Theme.of(context).colorScheme.onPrimaryContainer)),
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(item.name, style: const TextStyle(fontWeight: FontWeight.w600)),
                                      if (item.notes.isNotEmpty)
                                        Text(item.notes,
                                            style: TextStyle(
                                                color: Theme.of(context).colorScheme.onSurfaceVariant, fontSize: 12)),
                                    ],
                                  ),
                                ),
                                Text(_currencyFormat.format(item.lineTotal),
                                    style: const TextStyle(fontWeight: FontWeight.w600)),
                              ],
                            ),
                          )),
                      const Divider(height: 24),
                      _TotalRow('Subtotal', _currencyFormat.format(order.subtotal)),
                      if (order.discount > 0) _TotalRow('Discount', '-${_currencyFormat.format(order.discount)}'),
                      _TotalRow('VAT', _currencyFormat.format(order.tax)),
                      const SizedBox(height: 4),
                      _TotalRow('Total', _currencyFormat.format(order.total), emphasize: true),
                      const SizedBox(height: 8),
                    ],
                  ),
                ),
              ),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Change Status', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: orderStatusChoices.map((choice) {
                          final isCurrent = choice['value'] == order.status;
                          final color = statusColor(choice['value']!);
                          return ChoiceChip(
                            label: Text(choice['label']!),
                            selected: isCurrent,
                            selectedColor: color,
                            labelStyle: TextStyle(
                              color: isCurrent ? Colors.white : null,
                              fontWeight: FontWeight.w600,
                            ),
                            onSelected: (_updating || isCurrent) ? null : (_) => _updateStatus(choice['value']!),
                          );
                        }).toList(),
                      ),
                      if (_updating) ...[
                        const SizedBox(height: 12),
                        const Center(child: CircularProgressIndicator(strokeWidth: 2)),
                      ],
                    ],
                  ),
                ),
              ),
              if (order.statusLogs.isNotEmpty)
                Card(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Activity History', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
                        ...order.statusLogs.map((log) => ListTile(
                              contentPadding: EdgeInsets.zero,
                              dense: true,
                              leading: const Icon(Icons.history_rounded, size: 18),
                              title: Text(
                                '${log.changedByUsername ?? "Unknown"} · ${log.oldStatusDisplay} → ${log.newStatusDisplay}',
                                style: const TextStyle(fontSize: 13),
                              ),
                              subtitle: Text(DateFormat('dd/MM HH:mm').format(log.changedAt.toLocal())),
                            )),
                      ],
                    ),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final bool isLast;
  const _InfoRow(this.icon, this.label, this.value, {this.isLast = false});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: EdgeInsets.only(bottom: isLast ? 0 : 10),
      child: Row(
        children: [
          Icon(icon, size: 18, color: scheme.onSurfaceVariant),
          const SizedBox(width: 10),
          Text(label, style: TextStyle(color: scheme.onSurfaceVariant, fontSize: 13)),
          const Spacer(),
          Flexible(
            child: Text(value, textAlign: TextAlign.right, style: const TextStyle(fontWeight: FontWeight.w600)),
          ),
        ],
      ),
    );
  }
}

class _TotalRow extends StatelessWidget {
  final String label;
  final String value;
  final bool emphasize;
  const _TotalRow(this.label, this.value, {this.emphasize = false});

  @override
  Widget build(BuildContext context) {
    final style = emphasize
        ? const TextStyle(fontWeight: FontWeight.w800, fontSize: 17)
        : const TextStyle(fontSize: 13.5);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: emphasize ? style : style.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant)),
          Text(value, style: style),
        ],
      ),
    );
  }
}
