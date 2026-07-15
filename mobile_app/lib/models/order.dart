class OrderSummary {
  final int id;
  final String orderNumber;
  final String tableType;
  final String tableTypeDisplay;
  final String tableNumber;
  final String customerName;
  final double total;
  final String status;
  final String statusDisplay;
  final DateTime createdAt;

  OrderSummary({
    required this.id,
    required this.orderNumber,
    required this.tableType,
    required this.tableTypeDisplay,
    required this.tableNumber,
    required this.customerName,
    required this.total,
    required this.status,
    required this.statusDisplay,
    required this.createdAt,
  });

  bool get isSunbed => tableType == 'sunbed';

  factory OrderSummary.fromJson(Map<String, dynamic> json) {
    return OrderSummary(
      id: json['id'] as int,
      orderNumber: json['order_number'] as String? ?? '',
      tableType: json['table_type'] as String? ?? 'table',
      tableTypeDisplay: json['table_type_display'] as String? ?? 'Table',
      tableNumber: json['table_number'] as String? ?? '',
      customerName: json['customer_name'] as String? ?? '',
      total: double.parse(json['total'].toString()),
      status: json['status'] as String,
      statusDisplay: json['status_display'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}

class OrderItem {
  final int id;
  final String name;
  final double price;
  final int quantity;
  final double lineTotal;
  final String notes;

  OrderItem({
    required this.id,
    required this.name,
    required this.price,
    required this.quantity,
    required this.lineTotal,
    required this.notes,
  });

  factory OrderItem.fromJson(Map<String, dynamic> json) {
    return OrderItem(
      id: json['id'] as int,
      name: json['name'] as String,
      price: double.parse(json['price'].toString()),
      quantity: json['quantity'] as int,
      lineTotal: double.parse(json['line_total'].toString()),
      notes: json['notes'] as String? ?? '',
    );
  }
}

class OrderStatusLogEntry {
  final String? changedByUsername;
  final String oldStatusDisplay;
  final String newStatusDisplay;
  final DateTime changedAt;

  OrderStatusLogEntry({
    required this.changedByUsername,
    required this.oldStatusDisplay,
    required this.newStatusDisplay,
    required this.changedAt,
  });

  factory OrderStatusLogEntry.fromJson(Map<String, dynamic> json) {
    return OrderStatusLogEntry(
      changedByUsername: json['changed_by_username'] as String?,
      oldStatusDisplay: json['old_status_display'] as String? ?? '',
      newStatusDisplay: json['new_status_display'] as String,
      changedAt: DateTime.parse(json['changed_at'] as String),
    );
  }
}

class OrderDetail {
  final int id;
  final String orderNumber;
  final String tableType;
  final String tableTypeDisplay;
  final String tableNumber;
  final String customerName;
  final String customerPhone;
  final String customerNotes;
  final double subtotal;
  final double discount;
  final double tax;
  final double total;
  final String status;
  final String statusDisplay;
  final List<OrderItem> items;
  final List<OrderStatusLogEntry> statusLogs;
  final DateTime createdAt;

  bool get isSunbed => tableType == 'sunbed';

  OrderDetail({
    required this.id,
    required this.orderNumber,
    required this.tableType,
    required this.tableTypeDisplay,
    required this.tableNumber,
    required this.customerName,
    required this.customerPhone,
    required this.customerNotes,
    required this.subtotal,
    required this.discount,
    required this.tax,
    required this.total,
    required this.status,
    required this.statusDisplay,
    required this.items,
    required this.statusLogs,
    required this.createdAt,
  });

  factory OrderDetail.fromJson(Map<String, dynamic> json) {
    return OrderDetail(
      id: json['id'] as int,
      orderNumber: json['order_number'] as String? ?? '',
      tableType: json['table_type'] as String? ?? 'table',
      tableTypeDisplay: json['table_type_display'] as String? ?? 'Table',
      tableNumber: json['table_number'] as String? ?? '',
      customerName: json['customer_name'] as String? ?? '',
      customerPhone: json['customer_phone'] as String? ?? '',
      customerNotes: json['customer_notes'] as String? ?? '',
      subtotal: double.parse(json['subtotal'].toString()),
      discount: double.parse(json['discount'].toString()),
      tax: double.parse(json['tax'].toString()),
      total: double.parse(json['total'].toString()),
      status: json['status'] as String,
      statusDisplay: json['status_display'] as String,
      items: (json['order_items'] as List<dynamic>? ?? [])
          .map((e) => OrderItem.fromJson(e as Map<String, dynamic>))
          .toList(),
      statusLogs: (json['status_logs'] as List<dynamic>? ?? [])
          .map((e) => OrderStatusLogEntry.fromJson(e as Map<String, dynamic>))
          .toList(),
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}

/// Matches Order.ORDER_STATUS in orders/models.py - keep in sync with the backend.
const List<Map<String, String>> orderStatusChoices = [
  {'value': 'pending', 'label': 'Pending'},
  {'value': 'confirmed', 'label': 'Confirmed'},
  {'value': 'preparing', 'label': 'Preparing'},
  {'value': 'ready', 'label': 'Ready'},
  {'value': 'delivered', 'label': 'Delivered'},
  {'value': 'cancelled', 'label': 'Cancelled'},
];
