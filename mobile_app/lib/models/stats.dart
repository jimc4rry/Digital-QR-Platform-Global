class StatsPeriod {
  final double revenue;
  final int count;

  StatsPeriod({required this.revenue, required this.count});

  factory StatsPeriod.fromJson(Map<String, dynamic> json) {
    return StatsPeriod(
      revenue: (json['revenue'] as num).toDouble(),
      count: json['count'] as int,
    );
  }
}

class TopProduct {
  final String name;
  final int totalQuantity;
  final double totalRevenue;

  TopProduct({required this.name, required this.totalQuantity, required this.totalRevenue});

  factory TopProduct.fromJson(Map<String, dynamic> json) {
    return TopProduct(
      name: json['name'] as String,
      totalQuantity: json['total_quantity'] as int,
      totalRevenue: (json['total_revenue'] as num).toDouble(),
    );
  }
}

class TrendPoint {
  final String date;
  final double revenue;

  TrendPoint({required this.date, required this.revenue});

  factory TrendPoint.fromJson(Map<String, dynamic> json) {
    return TrendPoint(
      date: json['date'] as String,
      revenue: (json['revenue'] as num).toDouble(),
    );
  }
}

/// Mirrors GET /api/v1/stats/ - same Business-plan gate as stats_dashboard on the web.
class Stats {
  final bool available;
  final StatsPeriod? today;
  final StatsPeriod? week;
  final StatsPeriod? month;
  final List<TopProduct> topProducts;
  final List<TrendPoint> trend;

  Stats({
    required this.available,
    this.today,
    this.week,
    this.month,
    this.topProducts = const [],
    this.trend = const [],
  });

  factory Stats.fromJson(Map<String, dynamic> json) {
    if (json['available'] != true) return Stats(available: false);
    return Stats(
      available: true,
      today: StatsPeriod.fromJson(json['today'] as Map<String, dynamic>),
      week: StatsPeriod.fromJson(json['week'] as Map<String, dynamic>),
      month: StatsPeriod.fromJson(json['month'] as Map<String, dynamic>),
      topProducts: (json['top_products'] as List<dynamic>)
          .map((e) => TopProduct.fromJson(e as Map<String, dynamic>))
          .toList(),
      trend: (json['trend'] as List<dynamic>)
          .map((e) => TrendPoint.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}
