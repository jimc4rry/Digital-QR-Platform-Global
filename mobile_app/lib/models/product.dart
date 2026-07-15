class Product {
  final int id;
  final String name;
  final String nameEn;
  final String displayName;
  final String categoryName;
  final String description;
  final double price;
  final double? oldPrice;
  final String? imageUrl;
  final bool isAvailable;
  final bool isFeatured;
  final bool isVegan;
  final bool isVegetarian;
  final bool isGlutenFree;
  final bool isSpicy;

  Product({
    required this.id,
    required this.name,
    required this.nameEn,
    required this.displayName,
    required this.categoryName,
    required this.description,
    required this.price,
    this.oldPrice,
    this.imageUrl,
    required this.isAvailable,
    required this.isFeatured,
    required this.isVegan,
    required this.isVegetarian,
    required this.isGlutenFree,
    required this.isSpicy,
  });

  factory Product.fromJson(Map<String, dynamic> json) {
    return Product(
      id: json['id'] as int,
      name: json['name'] as String,
      nameEn: json['name_en'] as String? ?? '',
      displayName: json['display_name'] as String,
      categoryName: json['category_name'] as String? ?? '',
      description: json['description'] as String? ?? '',
      price: double.parse(json['price'].toString()),
      oldPrice: json['old_price'] != null ? double.parse(json['old_price'].toString()) : null,
      imageUrl: json['image_url'] as String?,
      isAvailable: json['is_available'] as bool,
      isFeatured: json['is_featured'] as bool,
      isVegan: json['is_vegan'] as bool,
      isVegetarian: json['is_vegetarian'] as bool,
      isGlutenFree: json['is_gluten_free'] as bool,
      isSpicy: json['is_spicy'] as bool,
    );
  }
}
