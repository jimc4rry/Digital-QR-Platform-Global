/// One admin/employee account under the owner's restaurant - mirrors
/// StaffMemberSerializer / staff_list.html on the web.
class StaffMember {
  final int id;
  final String username;
  final String role;
  final String roleDisplay;
  final DateTime createdAt;

  StaffMember({
    required this.id,
    required this.username,
    required this.role,
    required this.roleDisplay,
    required this.createdAt,
  });

  factory StaffMember.fromJson(Map<String, dynamic> json) {
    return StaffMember(
      id: json['id'] as int,
      username: json['username'] as String,
      role: json['role'] as String,
      roleDisplay: json['role_display'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}
