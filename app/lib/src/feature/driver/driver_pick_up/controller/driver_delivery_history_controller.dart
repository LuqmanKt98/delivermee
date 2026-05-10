import 'package:get/get.dart';
import '../../../../common/services/driver_api_service.dart';
import '../../../../models/delivery_model.dart';

class DriverDeliveryHistoryController extends GetxController {
  final RxList<DeliveryModel> deliveries = <DeliveryModel>[].obs;
  final RxBool isLoading = false.obs;
  final RxString errorMessage = ''.obs;
  final RxBool hasError = false.obs;

  // Pagination
  final RxInt currentOffset = 0.obs;
  final RxInt totalCount = 0.obs;
  final RxBool hasMoreData = true.obs;
  final int limit = 50;

  @override
  void onInit() {
    super.onInit();
    loadDeliveries();
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
          '🔄 Loading delivery history - Offset: ${currentOffset.value}, Limit: $limit');

      final response = await DriverApiService.getDriverDeliveryHistory(
        limit: limit,
        offset: currentOffset.value,
      );

      final newDeliveries =
          (response['deliveries'] as List<DeliveryModel>? ?? <DeliveryModel>[]);
      final total = (response['total'] as int?) ?? newDeliveries.length;

      print('📦 Received ${newDeliveries.length} completed deliveries');
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
      print('❌ Error loading delivery history: $e');
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
      case 'pickup_truck':
        return 'Pickup Truck';
      case 'cargo_van':
        return 'Cargo Van';
      default:
        return vehicleType;
    }
  }

  String getStatusDisplayName(String status) {
    switch (status.toLowerCase()) {
      case 'delivered':
        return 'Delivered';
      case 'cancelled':
        return 'Cancelled';
      default:
        return status;
    }
  }

  double calculateEarnings() {
    return deliveries.fold(0.0, (sum, delivery) {
      if (delivery.status.toLowerCase() == 'delivered' &&
          delivery.estimatedCost != null) {
        return sum + delivery.estimatedCost!;
      }
      return sum;
    });
  }

  int getDeliveredCount() {
    return deliveries
        .where((d) => d.status.toLowerCase() == 'delivered')
        .length;
  }

  int getCancelledCount() {
    return deliveries
        .where((d) => d.status.toLowerCase() == 'cancelled')
        .length;
  }
}
