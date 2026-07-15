import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../models/product.dart';
import '../services/api_client.dart';
import '../services/auth_service.dart';
import '../services/staff_repository.dart';
import '../widgets/empty_state.dart';

class ProductListScreen extends StatefulWidget {
  final bool canManageMenu;
  const ProductListScreen({super.key, required this.canManageMenu});

  @override
  State<ProductListScreen> createState() => _ProductListScreenState();
}

class _ProductListScreenState extends State<ProductListScreen> {
  late final StaffRepository _repository;
  late Future<List<Product>> _productsFuture;
  final _currencyFormat = NumberFormat.currency(locale: 'el_GR', symbol: '€');

  @override
  void initState() {
    super.initState();
    _repository = StaffRepository(ApiClient(context.read<AuthService>()));
    _load();
  }

  void _load() {
    final future = _repository.getProducts();
    setState(() {
      _productsFuture = future;
    });
  }

  Future<void> _toggleAvailability(Product product) async {
    try {
      await _repository.setProductAvailability(product.id, !product.isAvailable);
      _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e is ApiException ? e.message : 'Update failed.')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Products')),
      body: RefreshIndicator(
        onRefresh: () async => _load(),
        child: AsyncListView<List<Product>>(
          future: _productsFuture,
          onRetry: _load,
          builder: (context, products) {
            if (products.isEmpty) {
              return ListView(
                children: const [
                  SizedBox(height: 80),
                  EmptyState(icon: Icons.restaurant_menu_rounded, message: 'No products yet'),
                ],
              );
            }
            return ListView.builder(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
              itemCount: products.length,
              itemBuilder: (context, index) {
                final product = products[index];
                return _ProductCard(
                  product: product,
                  currencyFormat: _currencyFormat,
                  canManage: widget.canManageMenu,
                  onToggle: () => _toggleAvailability(product),
                );
              },
            );
          },
        ),
      ),
    );
  }
}

class _ProductCard extends StatelessWidget {
  final Product product;
  final NumberFormat currencyFormat;
  final bool canManage;
  final VoidCallback onToggle;

  const _ProductCard({
    required this.product,
    required this.currencyFormat,
    required this.canManage,
    required this.onToggle,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: product.imageUrl != null
                  ? Image.network(product.imageUrl!, width: 56, height: 56, fit: BoxFit.cover)
                  : Container(
                      width: 56,
                      height: 56,
                      color: scheme.surfaceContainerHighest,
                      child: Icon(Icons.restaurant_rounded, color: scheme.onSurfaceVariant),
                    ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(product.displayName,
                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14.5),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis),
                  const SizedBox(height: 3),
                  Text(
                    '${product.categoryName} · ${currencyFormat.format(product.price)}',
                    style: TextStyle(color: scheme.onSurfaceVariant, fontSize: 12.5),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            canManage
                ? Switch(value: product.isAvailable, onChanged: (_) => onToggle())
                : Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: (product.isAvailable ? Colors.green : Colors.red).withValues(alpha: 0.14),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      product.isAvailable ? 'Available' : 'Unavailable',
                      style: TextStyle(
                        color: product.isAvailable ? Colors.green.shade800 : Colors.red.shade800,
                        fontWeight: FontWeight.w700,
                        fontSize: 11,
                      ),
                    ),
                  ),
          ],
        ),
      ),
    );
  }
}
