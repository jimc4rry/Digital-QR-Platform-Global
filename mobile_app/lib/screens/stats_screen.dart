import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/stats.dart';
import '../services/staff_repository.dart';
import '../widgets/empty_state.dart';
import 'owner_tools_screen.dart';

class StatsScreen extends StatefulWidget {
  final StaffRepository repository;
  const StatsScreen({super.key, required this.repository});

  @override
  State<StatsScreen> createState() => _StatsScreenState();
}

class _StatsScreenState extends State<StatsScreen> {
  late Future<Stats> _statsFuture;
  final _currencyFormat = NumberFormat.currency(locale: 'el_GR', symbol: '€');

  @override
  void initState() {
    super.initState();
    _statsFuture = widget.repository.getStats();
  }

  void _reload() {
    final future = widget.repository.getStats();
    setState(() {
      _statsFuture = future;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Statistics')),
      body: RefreshIndicator(
        onRefresh: () async => _reload(),
        child: AsyncListView<Stats>(
          future: _statsFuture,
          onRetry: _reload,
          builder: (context, stats) {
            if (!stats.available) {
              return ListView(children: const [
                SizedBox(height: 80),
                UpgradeRequiredView(message: 'Statistics are available on the Business plan.'),
              ]);
            }
            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Row(
                  children: [
                    Expanded(
                      child: _PeriodCard(
                          label: 'Today', icon: Icons.today_rounded, color: Colors.indigo,
                          period: stats.today!, format: _currencyFormat),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: _PeriodCard(
                          label: 'Week', icon: Icons.view_week_rounded, color: Colors.teal,
                          period: stats.week!, format: _currencyFormat),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: _PeriodCard(
                          label: 'Month', icon: Icons.calendar_month_rounded, color: Colors.orange,
                          period: stats.month!, format: _currencyFormat),
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Revenue for the last 14 days', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
                        const SizedBox(height: 16),
                        _TrendChart(trend: stats.trend, format: _currencyFormat),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Popular Products', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
                        const SizedBox(height: 4),
                        if (stats.topProducts.isEmpty)
                          const Padding(
                            padding: EdgeInsets.symmetric(vertical: 16),
                            child: EmptyState(icon: Icons.insights_rounded, message: 'No data available yet.'),
                          )
                        else
                          ...stats.topProducts.asMap().entries.map((entry) {
                            final rank = entry.key + 1;
                            final p = entry.value;
                            return ListTile(
                              contentPadding: EdgeInsets.zero,
                              leading: CircleAvatar(
                                radius: 16,
                                backgroundColor: Theme.of(context).colorScheme.primaryContainer,
                                child: Text('$rank', style: TextStyle(
                                    fontWeight: FontWeight.w700,
                                    fontSize: 12,
                                    color: Theme.of(context).colorScheme.onPrimaryContainer)),
                              ),
                              title: Text(p.name, style: const TextStyle(fontWeight: FontWeight.w600)),
                              subtitle: Text('${p.totalQuantity} pcs'),
                              trailing: Text(_currencyFormat.format(p.totalRevenue),
                                  style: const TextStyle(fontWeight: FontWeight.w700)),
                            );
                          }),
                      ],
                    ),
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _PeriodCard extends StatelessWidget {
  final String label;
  final IconData icon;
  final Color color;
  final StatsPeriod period;
  final NumberFormat format;

  const _PeriodCard({
    required this.label,
    required this.icon,
    required this.color,
    required this.period,
    required this.format,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 30,
              height: 30,
              decoration: BoxDecoration(color: color.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(9)),
              child: Icon(icon, size: 16, color: color),
            ),
            const SizedBox(height: 10),
            Text(label, style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant, fontSize: 11.5)),
            const SizedBox(height: 2),
            Text(format.format(period.revenue),
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15), maxLines: 1, overflow: TextOverflow.ellipsis),
            Text('${period.count} orders', style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant, fontSize: 10.5)),
          ],
        ),
      ),
    );
  }
}

class _TrendChart extends StatelessWidget {
  final List<TrendPoint> trend;
  final NumberFormat format;
  const _TrendChart({required this.trend, required this.format});

  @override
  Widget build(BuildContext context) {
    final maxRevenue = trend.map((t) => t.revenue).fold<double>(0, (a, b) => a > b ? a : b);
    final scheme = Theme.of(context).colorScheme;
    return SizedBox(
      height: 140,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: trend.map((point) {
          final heightFraction = maxRevenue > 0 ? point.revenue / maxRevenue : 0.0;
          final isPeak = maxRevenue > 0 && point.revenue == maxRevenue;
          return Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 2),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  Tooltip(
                    message: format.format(point.revenue),
                    child: Container(
                      height: 4 + 96 * heightFraction,
                      decoration: BoxDecoration(
                        color: isPeak ? scheme.primary : scheme.primary.withValues(alpha: 0.35),
                        borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
                      ),
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(point.date, style: TextStyle(fontSize: 8, color: scheme.onSurfaceVariant), textAlign: TextAlign.center),
                ],
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}
