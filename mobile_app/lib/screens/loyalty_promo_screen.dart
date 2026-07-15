import 'package:flutter/material.dart';
import '../models/loyalty_account.dart';
import '../models/promo_code.dart';
import '../services/api_client.dart';
import '../services/staff_repository.dart';
import '../widgets/empty_state.dart';
import 'owner_tools_screen.dart';

class LoyaltyPromoScreen extends StatelessWidget {
  final StaffRepository repository;
  const LoyaltyPromoScreen({super.key, required this.repository});

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Loyalty & Promo'),
          bottom: const TabBar(tabs: [Tab(text: 'Loyalty'), Tab(text: 'Promo Codes')]),
        ),
        body: TabBarView(
          children: [
            _LoyaltyTab(repository: repository),
            _PromoCodeTab(repository: repository),
          ],
        ),
      ),
    );
  }
}

class _LoyaltyTab extends StatefulWidget {
  final StaffRepository repository;
  const _LoyaltyTab({required this.repository});

  @override
  State<_LoyaltyTab> createState() => _LoyaltyTabState();
}

class _LoyaltyTabState extends State<_LoyaltyTab> {
  late Future<(bool, List<LoyaltyAccount>)> _accountsFuture;
  final _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    final future = widget.repository.getLoyaltyAccounts(search: _searchController.text.trim());
    setState(() {
      _accountsFuture = future;
    });
  }

  Future<void> _editPoints(LoyaltyAccount account) async {
    final controller = TextEditingController(text: account.points.toString());
    final newPoints = await showDialog<int>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(account.phone),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'Points', prefixIcon: Icon(Icons.star_outline_rounded)),
          autofocus: true,
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          FilledButton(
            onPressed: () => Navigator.pop(context, int.tryParse(controller.text)),
            child: const Text('Save'),
          ),
        ],
      ),
    );
    if (newPoints == null) return;
    try {
      await widget.repository.updateLoyaltyPoints(account.id, newPoints);
      _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e is ApiException ? e.message : 'Update failed.')),
        );
      }
    }
  }

  Future<void> _deleteAccount(LoyaltyAccount account) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Loyalty Account'),
        content: Text('Are you sure you want to delete the account "${account.phone}"?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          FilledButton.tonal(
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.errorContainer,
              foregroundColor: Theme.of(context).colorScheme.onErrorContainer,
            ),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await widget.repository.deleteLoyaltyAccount(account.id);
      _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e is ApiException ? e.message : 'Delete failed.')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(16),
          child: TextField(
            controller: _searchController,
            decoration: InputDecoration(
              hintText: 'Search by phone',
              prefixIcon: const Icon(Icons.search_rounded),
              suffixIcon: IconButton(
                icon: const Icon(Icons.clear_rounded),
                onPressed: () {
                  _searchController.clear();
                  _load();
                },
              ),
            ),
            onSubmitted: (_) => _load(),
          ),
        ),
        Expanded(
          child: RefreshIndicator(
            onRefresh: () async => _load(),
            child: AsyncListView<(bool, List<LoyaltyAccount>)>(
              future: _accountsFuture,
              onRetry: _load,
              builder: (context, data) {
                final (available, accounts) = data;
                if (!available) {
                  return ListView(children: const [
                    SizedBox(height: 60),
                    UpgradeRequiredView(message: 'Loyalty is available starting from the Pro plan.'),
                  ]);
                }
                if (accounts.isEmpty) {
                  return ListView(children: const [
                    SizedBox(height: 60),
                    EmptyState(icon: Icons.star_outline_rounded, message: 'No loyalty accounts found.'),
                  ]);
                }
                return ListView.builder(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                  itemCount: accounts.length,
                  itemBuilder: (context, index) {
                    final account = accounts[index];
                    return Card(
                      child: ListTile(
                        leading: CircleAvatar(
                          backgroundColor: Colors.amber.withValues(alpha: 0.18),
                          child: Icon(Icons.star_rounded, color: Colors.amber.shade800),
                        ),
                        title: Text(account.phone, style: const TextStyle(fontWeight: FontWeight.w700)),
                        subtitle: Text('${account.points} points'),
                        trailing: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            IconButton(
                              icon: const Icon(Icons.edit_outlined),
                              onPressed: () => _editPoints(account),
                            ),
                            IconButton(
                              icon: const Icon(Icons.delete_outline_rounded, color: Colors.red),
                              onPressed: () => _deleteAccount(account),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                );
              },
            ),
          ),
        ),
      ],
    );
  }
}

class _PromoCodeTab extends StatefulWidget {
  final StaffRepository repository;
  const _PromoCodeTab({required this.repository});

  @override
  State<_PromoCodeTab> createState() => _PromoCodeTabState();
}

class _PromoCodeTabState extends State<_PromoCodeTab> {
  late Future<(bool, List<PromoCode>)> _promoFuture;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    final future = widget.repository.getPromoCodes();
    setState(() {
      _promoFuture = future;
    });
  }

  Future<void> _deletePromo(PromoCode promo) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Code'),
        content: Text('Are you sure you want to delete the code "${promo.code}"?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          FilledButton.tonal(
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.errorContainer,
              foregroundColor: Theme.of(context).colorScheme.onErrorContainer,
            ),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await widget.repository.deletePromoCode(promo.id);
      _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e is ApiException ? e.message : 'Delete failed.')),
        );
      }
    }
  }

  Future<void> _openCreateDialog() async {
    final formKey = GlobalKey<FormState>();
    final codeController = TextEditingController();
    final discountController = TextEditingController();
    final maxUsesController = TextEditingController();
    String? errorText;

    final created = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('New Discount Code'),
          content: Form(
            key: formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextFormField(
                  controller: codeController,
                  decoration: const InputDecoration(
                      labelText: 'Code (e.g. SAVE10)', prefixIcon: Icon(Icons.local_offer_outlined)),
                  textCapitalization: TextCapitalization.characters,
                  validator: (v) => (v == null || v.trim().isEmpty) ? 'Required field' : null,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: discountController,
                  decoration: const InputDecoration(labelText: 'Discount (%)', prefixIcon: Icon(Icons.percent_rounded)),
                  keyboardType: TextInputType.number,
                  validator: (v) {
                    final n = int.tryParse(v ?? '');
                    if (n == null || n < 1 || n > 100) return 'Value 1-100';
                    return null;
                  },
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: maxUsesController,
                  decoration: const InputDecoration(
                      labelText: 'Max uses (optional)', prefixIcon: Icon(Icons.numbers_rounded)),
                  keyboardType: TextInputType.number,
                ),
                if (errorText != null) ...[
                  const SizedBox(height: 10),
                  Text(errorText!, style: TextStyle(color: Theme.of(context).colorScheme.error, fontSize: 13)),
                ],
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
            FilledButton(
              onPressed: () async {
                if (!(formKey.currentState?.validate() ?? false)) return;
                try {
                  await widget.repository.createPromoCode(
                    code: codeController.text.trim(),
                    discountPercent: int.parse(discountController.text),
                    maxUses: int.tryParse(maxUsesController.text),
                  );
                  if (context.mounted) Navigator.pop(context, true);
                } catch (e) {
                  setDialogState(() {
                    errorText = e is ApiException ? e.message : 'Something went wrong.';
                  });
                }
              },
              child: const Text('Create'),
            ),
          ],
        ),
      ),
    );
    if (created == true) _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _openCreateDialog,
        icon: const Icon(Icons.add_rounded),
        label: const Text('New Code'),
      ),
      body: RefreshIndicator(
        onRefresh: () async => _load(),
        child: AsyncListView<(bool, List<PromoCode>)>(
          future: _promoFuture,
          onRetry: _load,
          builder: (context, data) {
            final (available, promoCodes) = data;
            if (!available) {
              return ListView(children: const [
                SizedBox(height: 60),
                UpgradeRequiredView(message: 'Discount codes are available starting from the Pro plan.'),
              ]);
            }
            if (promoCodes.isEmpty) {
              return ListView(children: const [
                SizedBox(height: 60),
                EmptyState(icon: Icons.local_offer_outlined, message: 'No discount codes yet.'),
              ]);
            }
            return ListView.builder(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 88),
              itemCount: promoCodes.length,
              itemBuilder: (context, index) {
                final promo = promoCodes[index];
                return Card(
                  child: ListTile(
                    leading: CircleAvatar(
                      backgroundColor: Theme.of(context).colorScheme.primaryContainer,
                      child: Text('${promo.discountPercent}%',
                          style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w800,
                              color: Theme.of(context).colorScheme.onPrimaryContainer)),
                    ),
                    title: Text(promo.code, style: const TextStyle(fontWeight: FontWeight.w700)),
                    subtitle: Text(
                      '${promo.usedCount}${promo.maxUses != null ? '/${promo.maxUses}' : ''} uses'
                      '${promo.isActive ? '' : ' · Inactive'}',
                    ),
                    trailing: IconButton(
                      icon: const Icon(Icons.delete_outline_rounded, color: Colors.red),
                      onPressed: () => _deletePromo(promo),
                    ),
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }
}
