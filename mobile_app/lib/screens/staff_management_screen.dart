import 'package:flutter/material.dart';
import '../models/staff_member.dart';
import '../services/api_client.dart';
import '../services/staff_repository.dart';
import '../widgets/empty_state.dart';
import 'owner_tools_screen.dart';

class StaffManagementScreen extends StatefulWidget {
  final StaffRepository repository;
  const StaffManagementScreen({super.key, required this.repository});

  @override
  State<StaffManagementScreen> createState() => _StaffManagementScreenState();
}

class _StaffManagementScreenState extends State<StaffManagementScreen> {
  late Future<(bool, List<StaffMember>)> _staffFuture;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    final future = widget.repository.getStaff();
    setState(() {
      _staffFuture = future;
    });
  }

  Future<void> _confirmDelete(StaffMember member) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Remove Staff Member'),
        content: Text('Are you sure you want to remove "${member.username}"?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          FilledButton.tonal(
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.errorContainer,
              foregroundColor: Theme.of(context).colorScheme.onErrorContainer,
            ),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Remove'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await widget.repository.deleteStaff(member.id);
      _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e is ApiException ? e.message : 'Remove failed.')),
        );
      }
    }
  }

  Future<void> _openCreateDialog() async {
    final formKey = GlobalKey<FormState>();
    final usernameController = TextEditingController();
    final passwordController = TextEditingController();
    String role = 'employee';
    String? errorText;
    bool obscurePassword = true;

    final created = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('New Account'),
          content: Form(
            key: formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextFormField(
                  controller: usernameController,
                  decoration: const InputDecoration(labelText: 'Username', prefixIcon: Icon(Icons.person_outline_rounded)),
                  validator: (v) => (v == null || v.trim().isEmpty) ? 'Required field' : null,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: passwordController,
                  decoration: InputDecoration(
                    labelText: 'Password',
                    prefixIcon: const Icon(Icons.lock_outline_rounded),
                    suffixIcon: IconButton(
                      icon: Icon(obscurePassword ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                      onPressed: () => setDialogState(() => obscurePassword = !obscurePassword),
                    ),
                  ),
                  obscureText: obscurePassword,
                  validator: (v) => (v == null || v.length < 8) ? 'At least 8 characters' : null,
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  initialValue: role,
                  decoration: const InputDecoration(labelText: 'Role', prefixIcon: Icon(Icons.badge_outlined)),
                  items: const [
                    DropdownMenuItem(value: 'employee', child: Text('Employee')),
                    DropdownMenuItem(value: 'admin', child: Text('Admin')),
                  ],
                  onChanged: (v) => role = v ?? 'employee',
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
                  await widget.repository.createStaff(
                    usernameController.text.trim(),
                    passwordController.text,
                    role,
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
      appBar: AppBar(title: const Text('Staff')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _openCreateDialog,
        icon: const Icon(Icons.person_add_alt_1_rounded),
        label: const Text('New'),
      ),
      body: RefreshIndicator(
        onRefresh: () async => _load(),
        child: AsyncListView<(bool, List<StaffMember>)>(
          future: _staffFuture,
          onRetry: _load,
          builder: (context, data) {
            final (available, members) = data;
            if (!available) {
              return ListView(children: const [
                SizedBox(height: 80),
                UpgradeRequiredView(message: 'Staff management is available on the Business plan.'),
              ]);
            }
            if (members.isEmpty) {
              return ListView(children: const [
                SizedBox(height: 80),
                EmptyState(icon: Icons.people_outline_rounded, message: 'No staff accounts yet.'),
              ]);
            }
            return ListView.builder(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 88),
              itemCount: members.length,
              itemBuilder: (context, index) {
                final member = members[index];
                final isAdmin = member.role == 'admin';
                return Card(
                  child: ListTile(
                    leading: CircleAvatar(
                      backgroundColor: (isAdmin ? Colors.orange : Colors.teal).withValues(alpha: 0.16),
                      child: Text(member.username[0].toUpperCase(),
                          style: TextStyle(
                              color: isAdmin ? Colors.orange.shade800 : Colors.teal.shade800,
                              fontWeight: FontWeight.w700)),
                    ),
                    title: Text(member.username, style: const TextStyle(fontWeight: FontWeight.w700)),
                    subtitle: Text(member.roleDisplay),
                    trailing: IconButton(
                      icon: const Icon(Icons.delete_outline_rounded, color: Colors.red),
                      onPressed: () => _confirmDelete(member),
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
