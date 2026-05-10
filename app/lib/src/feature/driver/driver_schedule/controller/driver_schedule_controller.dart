import 'package:get/get.dart';
import '../../../../common/services/driver_api_service.dart';
import '../../../../models/delivery_model.dart';

class DriverScheduleController extends GetxController {
  final RxList<DeliveryModel> deliveries = <DeliveryModel>[].obs;
  final RxBool isLoading = false.obs;
  final RxString errorMessage = ''.obs;
  final RxBool hasError = false.obs;

  // Pagination
  final RxInt currentOffset = 0.obs;
  final RxInt totalCount = 0.obs;
  final RxBool hasMoreData = true.obs;
  final int limit = 50;
  final int days = 7;

  @override
  void onInit() {
    super.onInit();
    // Auto-load deliveries when the controller is initialized
    loadDeliveries();
  }

  /// Insert/update an accepted delivery locally so it appears immediately
  /// in the Scheduled tab after the driver accepts it.
  void addAcceptedDelivery(DeliveryModel delivery) {
    // Clear any previous error so UI can show the list.
    hasError.value = false;
    errorMessage.value = '';

    deliveries.removeWhere((d) => d.id == delivery.id);
    deliveries.insert(0, delivery);

    // Keep pagination counters coherent for UI
    totalCount.value = deliveries.length;
    currentOffset.value = deliveries.length;
    hasMoreData.value = false;
  }

  Future<void> loadDeliveries({bool refresh = false}) async {
    try {
      if (refresh) {
        currentOffset.value = 0;
        hasMoreData.value = true;
        deliveries.clear();
      }

      if (!hasMoreData.value && !refresh) return;

      isLoading.value = true;
      hasError.value = false;
      errorMessage.value = '';

      print(
          '🔄 Loading deliveries - Offset: ${currentOffset.value}, Limit: $limit');

      final response = await DriverApiService.getDriverAcceptedDeliveries(
        limit: limit,
        offset: currentOffset.value,
        days: days,
      );

      final newDeliveries =
          (response['deliveries'] as List<DeliveryModel>? ?? <DeliveryModel>[]);
      final total = (response['total'] as int?) ?? newDeliveries.length;

      print('📦 Received ${newDeliveries.length} accepted deliveries');
      print('📊 Total count: $total');

      if (refresh) {
        deliveries.value = newDeliveries;
      } else {
        deliveries.addAll(newDeliveries);
      }

      totalCount.value = total;
      currentOffset.value += newDeliveries.length;

      // Check if we have more data to load
      hasMoreData.value = deliveries.length < totalCount.value;

      print('✅ Loaded ${deliveries.length}/${totalCount.value} deliveries');
    } catch (e) {
      print('❌ Error loading deliveries: $e');
      hasError.value = true;
      errorMessage.value = e.toString();
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> refreshDeliveries() async {
    await loadDeliveries(refresh: true);
  }

  Future<void> loadMoreDeliveries() async {
    if (!isLoading.value && hasMoreData.value) {
      await loadDeliveries();
    }
  }

  String formatDate(String? dateString) {
    if (dateString == null) return 'N/A';

    try {
      final date = DateTime.parse(dateString);
      return '${date.day.toString().padLeft(2, '0')}/${date.month.toString().padLeft(2, '0')}/${date.year}';
    } catch (e) {
      return 'N/A';
    }
  }

  String formatTime(String? timeString) {
    if (timeString == null) return 'N/A';

    try {
      final time = DateTime.parse(timeString);
      final hour = time.hour;
      final minute = time.minute.toString().padLeft(2, '0');
      final period = hour >= 12 ? 'PM' : 'AM';
      final displayHour = hour > 12 ? hour - 12 : (hour == 0 ? 12 : hour);
      return '$displayHour:$minute $period';
    } catch (e) {
      return 'N/A';
    }
  }

  String getVehicleTypeDisplayName(String vehicleType) {
    switch (vehicleType.toLowerCase()) {
      case 'sedan':
        return 'Sedan';
      case 'suv':
        return 'SUV';
      case 'truck':
        return 'Truck';
      case 'van':
        return 'Van';
      case 'motorcycle':
        return 'Motorcycle';
      default:
        return vehicleType;
    }
  }

  String getPackageTypeDisplayName(String packageType) {
    switch (packageType.toLowerCase()) {
      case 'small':
        return 'Small Package';
      case 'medium':
        return 'Medium Package';
      case 'large':
        return 'Large Package';
      case 'extra_large':
        return 'Extra Large Package';
      default:
        return packageType;
    }
  }

  String getStatusDisplayName(String status) {
    switch (status.toLowerCase()) {
      case 'assigned':
        return 'Assigned';
      case 'accepted':
        return 'Accepted';
      case 'picked_up':
        return 'Picked Up';
      case 'in_transit':
        return 'In Transit';
      case 'delivered':
        return 'Delivered';
      case 'cancelled':
        return 'Cancelled';
      default:
        return status;
    }
  }
}
