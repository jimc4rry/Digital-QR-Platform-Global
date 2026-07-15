import 'package:flutter/material.dart';
import '../models/restaurant_settings.dart';
import '../services/api_client.dart';
import '../services/staff_repository.dart';

class RestaurantSettingsScreen extends StatefulWidget {
  final StaffRepository repository;
  const RestaurantSettingsScreen({super.key, required this.repository});

  @override
  State<RestaurantSettingsScreen> createState() => _RestaurantSettingsScreenState();
}

class _RestaurantSettingsScreenState extends State<RestaurantSettingsScreen> {
  late Future<RestaurantSettings> _settingsFuture;
  final _formKey = GlobalKey<FormState>();

  late TextEditingController _nameController;
  late TextEditingController _descriptionController;
  late TextEditingController _addressController;
  late TextEditingController _phoneController;
  late TextEditingController _emailController;
  late TextEditingController _taxRateController;
  bool _allowOrdering = false;
  bool _loyaltyEnabled = false;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _settingsFuture = widget.repository.getSettings().then((settings) {
      _nameController = TextEditingController(text: settings.name);
      _descriptionController = TextEditingController(text: settings.description);
      _addressController = TextEditingController(text: settings.address);
      _phoneController = TextEditingController(text: settings.phone);
      _emailController = TextEditingController(text: settings.email);
      _taxRateController = TextEditingController(text: settings.taxRate.toString());
      _allowOrdering = settings.allowOrdering;
      _loyaltyEnabled = settings.loyaltyEnabled;
      return settings;
    });
  }

  Future<void> _save() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    setState(() => _saving = true);
    try {
      await widget.repository.updateSettings({
        'name': _nameController.text.trim(),
        'description': _descriptionController.text.trim(),
        'address': _addressController.text.trim(),
        'phone': _phoneController.text.trim(),
        'email': _emailController.text.trim(),
        'allow_ordering': _allowOrdering,
        'loyalty_enabled': _loyaltyEnabled,
        'tax_rate': double.tryParse(_taxRateController.text.replaceAll(',', '.')) ?? 0,
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Row(children: [
              Icon(Icons.check_circle_rounded, color: Colors.white, size: 18),
              SizedBox(width: 10),
              Text('Settings saved successfully!'),
            ]),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e is ApiException ? e.message : 'Save failed.')),
        );
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Restaurant Settings')),
      body: FutureBuilder<RestaurantSettings>(
        future: _settingsFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            final message =
                snapshot.error is ApiException ? (snapshot.error as ApiException).message : 'Something went wrong.';
            return Center(child: Padding(padding: const EdgeInsets.all(32), child: Text(message)));
          }
          return Form(
            key: _formKey,
            child: ListView(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
              children: [
                _SectionCard(
                  title: 'Contact Details',
                  icon: Icons.storefront_rounded,
                  children: [
                    TextFormField(
                      controller: _nameController,
                      decoration: const InputDecoration(labelText: 'Restaurant Name', prefixIcon: Icon(Icons.badge_outlined)),
                      validator: (v) => (v == null || v.trim().isEmpty) ? 'Required field' : null,
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _descriptionController,
                      decoration: const InputDecoration(labelText: 'Description', prefixIcon: Icon(Icons.notes_rounded)),
                      maxLines: 3,
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _addressController,
                      decoration: const InputDecoration(labelText: 'Address', prefixIcon: Icon(Icons.place_outlined)),
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _phoneController,
                      decoration: const InputDecoration(labelText: 'Phone', prefixIcon: Icon(Icons.call_outlined)),
                      keyboardType: TextInputType.phone,
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _emailController,
                      decoration: const InputDecoration(labelText: 'Email', prefixIcon: Icon(Icons.email_outlined)),
                      keyboardType: TextInputType.emailAddress,
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                _SectionCard(
                  title: 'Orders & VAT',
                  icon: Icons.receipt_long_rounded,
                  children: [
                    TextFormField(
                      controller: _taxRateController,
                      decoration: const InputDecoration(labelText: 'VAT (%)', prefixIcon: Icon(Icons.percent_rounded)),
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    ),
                    const SizedBox(height: 4),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Accept orders'),
                      value: _allowOrdering,
                      onChanged: (v) => setState(() => _allowOrdering = v),
                    ),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Enable Loyalty'),
                      subtitle: const Text('Points for customers'),
                      value: _loyaltyEnabled,
                      onChanged: (v) => setState(() => _loyaltyEnabled = v),
                    ),
                  ],
                ),
                const SizedBox(height: 24),
                FilledButton.icon(
                  onPressed: _saving ? null : _save,
                  icon: _saving
                      ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : const Icon(Icons.save_rounded),
                  label: const Text('Save'),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _SectionCard extends StatelessWidget {
  final String title;
  final IconData icon;
  final List<Widget> children;
  const _SectionCard({required this.title, required this.icon, required this.children});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, size: 18, color: scheme.primary),
                const SizedBox(width: 8),
                Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
              ],
            ),
            const SizedBox(height: 14),
            ...children,
          ],
        ),
      ),
    );
  }
}
