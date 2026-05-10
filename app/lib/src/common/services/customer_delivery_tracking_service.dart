import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:get/get.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../constant/api_config.dart';

class CustomerDeliveryTrackingService extends GetxService {
  static CustomerDeliveryTrackingService get to =>
      Get.find<CustomerDeliveryTrackingService>();

  // Using centralized API configuration
  String get baseUrl => ApiConfig.baseUrl;

  // Tracking state
  final RxString currentStatus = ''.obs;
  final RxString statusMessage = ''.obs;
  final RxString subStatusMessage = ''.obs;
  final RxDouble progressValue = 0.0.obs;
  final RxBool isLoading = false.obs;
  final RxString error = ''.obs;

  // Driver information
  final RxString driverName = ''.obs;
  final RxString driverPhone = ''.obs;
  final RxString driverRating = ''.obs;
  final RxString estimatedArrival = ''.obs;

  // Delivery information
  final RxMap<String, dynamic> deliveryData = <String, dynamic>{}.obs;
  final RxMap<String, dynamic> driverData = <String, dynamic>{}.obs;

  // Polling control
  Timer? _pollingTimer;
  final RxBool isPolling = false.obs;

  @override
  void onInit() {
    super.onInit();
  }

  @override
  void onClose() {
    _stopPolling();
    super.onClose();
  }

  /// Start tracking a delivery
  Future<void> startTracking(int deliveryId) async {
    try {
      isLoading.value = true;
      error.value = '';

      print('📱 Starting delivery tracking for ID: $deliveryId');

      // Get initial delivery status
      await _fetchDeliveryStatus(deliveryId);

      // Start polling for updates
      _startPolling(deliveryId);

      print('✅ Delivery tracking started');
    } catch (e) {
      print('❌ Error starting tracking: $e');
      error.value = 'Failed to start tracking: $e';
    } finally {
      isLoading.value = false;
    }
  }

  /// Manually refresh delivery status
  Future<void> refreshStatus(int deliveryId) async {
    try {
      print('🔄 Manually refreshing delivery status for ID: $deliveryId');

      // Fetch the latest status
      await _fetchDeliveryStatus(deliveryId);

      print('✅ Delivery status refreshed successfully');
    } catch (e) {
      print('❌ Error refreshing status: $e');
      error.value = 'Failed to refresh status: ${e.toString()}';
      rethrow;
    }
  }

  /// Stop tracking
  void stopTracking() {
    _stopPolling();
    print('🛑 Delivery tracking stopped');
  }

  /// Fetch current delivery status
  Future<void> _fetchDeliveryStatus(int deliveryId) async {
    try {
      final url = Uri.parse('$baseUrl/deliveries/$deliveryId/status');

      print('🔍 Fetching delivery status from: $url');

      final response = await http.get(
        url,
        headers: await _getHeaders(),
      );

      print(
          '📡 Delivery status response: ${response.statusCode} - ${response.body}');

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        print('📦 Parsed response data: $data');
        print('📦 Status field from response: ${data['status']}');
        await _handleStatusUpdate(data);
      } else {
        throw Exception(
            'Failed to fetch delivery status: ${response.statusCode}');
      }
    } catch (e) {
      print('❌ Error fetching delivery status: $e');
      throw e;
    }
  }

  /// Handle status updates from the server
  Future<void> _handleStatusUpdate(Map<String, dynamic> data) async {
    final status = data['status']?.toString().toLowerCase() ?? '';
    
    // Backend returns delivery fields at top level, not nested
    // So we use the data itself as delivery data
    final delivery = data;
    
    // Driver is at top level if present
    final driver =
        (data['driver'] as Map<String, dynamic>?) ?? <String, dynamic>{};

    print('📊 Status update received: $status');
    print('📊 Previous status: ${currentStatus.value}');
    print('📊 Delivery data keys: ${delivery.keys.toList()}');
    print('📊 Driver data: ${driver.toString()}');

    final statusChanged = currentStatus.value != status;
    if (statusChanged) {
      print('✅ Status changed from ${currentStatus.value} to $status');
    } else {
      print('⚠️ Status unchanged, but updating delivery data');
    }

    // Always update delivery and driver data (in case other fields changed)
    deliveryData.value = delivery;
    driverData.value = driver;

    // If driver data is empty but driver_id exists in delivery, fetch driver details
    if (driver.isEmpty && delivery['driver_id'] != null) {
      final driverId = delivery['driver_id'].toString();
      print('🔍 Driver data empty, fetching driver details for ID: $driverId');
      await _fetchDriverDetails(driverId);
    }

    // Update driver information from backend response format
    if (driver.isNotEmpty) {
      // Backend returns 'full_name', fallback to first_name + last_name
      driverName.value = driver['full_name'] ??
          '${driver['first_name'] ?? ''} ${driver['last_name'] ?? ''}'.trim() ??
          'Driver';

      // Backend returns phone in 'phone' field (mapped from phone_number)
      driverPhone.value = driver['phone']?.toString() ?? 
                          driver['phone_number']?.toString() ?? '';

      // Backend returns rating as float
      driverRating.value = driver['rating']?.toString() ?? '5.0';

      // Estimated arrival - not in backend response, keep default
      estimatedArrival.value = driver['estimated_arrival'] ?? '5-10 minutes';

      print(
          '👤 Driver info updated: ${driverName.value}, Rating: ${driverRating.value}, Phone: ${driverPhone.value.isNotEmpty ? "Available" : "Not available"}');
    }

    // Handle different statuses - match backend status format
    // Backend uses _map_status_to_expected_format, so handle all variations
    switch (status) {
      case 'confirmed':
      case 'pending':
        // Check if driver has been assigned even if status is still confirmed
        if (delivery['driver_id'] != null || driver.isNotEmpty) {
          print(
              '🔍 Driver assigned but status still confirmed, handling as accepted');
          _handleDriverAccepted();
        } else {
          _handleConfirmed();
        }
        break;
      case 'assigned':
      case 'accepted':
        _handleDriverAccepted();
        break;
      case 'picked_up':
      case 'pickedup':
        _handlePackagePickedUp();
        break;
      case 'in_transit':
      case 'in-transit':
      case 'intransit':
        _handleInTransit();
        break;
      case 'delivered':
      case 'completed':
        _handleDelivered();
        break;
      case 'cancelled':
      case 'canceled':
        _handleCancelled();
        break;
      default:
        print('⚠️ Unknown status received: $status');
        _handleUnknownStatus(status);
    }
  }

  /// Handle confirmed status
  void _handleConfirmed() {
    currentStatus.value = 'confirmed';
    statusMessage.value = 'Searching for drivers...';
    subStatusMessage.value = 'Looking for available drivers in your area';
    progressValue.value = 0.3;
  }

  /// Handle driver accepted
  void _handleDriverAccepted() {
    currentStatus.value = 'accepted';
    statusMessage.value = 'Driver Found!';
    subStatusMessage.value =
        '${driverName.value} is on their way to pick up your Item';
    progressValue.value = 0.5;
  }

  /// Handle package picked up
  void _handlePackagePickedUp() {
    currentStatus.value = 'picked_up';
    statusMessage.value = 'Item Picked Up!';
    subStatusMessage.value =
        '${driverName.value.isNotEmpty ? driverName.value : 'Your driver'} has picked up your Item and is on the way';
    progressValue.value = 0.7;
  }

  /// Handle in transit
  void _handleInTransit() {
    currentStatus.value = 'in_transit';
    statusMessage.value = 'Item In Transit';
    subStatusMessage.value = 'Your Item is on its way to the destination';
    progressValue.value = 0.8;
  }

  /// Handle delivered
  void _handleDelivered() {
    currentStatus.value = 'delivered';
    statusMessage.value = 'Item Delivered!';
    subStatusMessage.value = 'Your Item has been successfully delivered';
    progressValue.value = 1.0;
    _stopPolling(); // Stop polling when delivered
  }

  /// Handle cancelled
  void _handleCancelled() {
    currentStatus.value = 'cancelled';
    statusMessage.value = 'Delivery Cancelled';
    subStatusMessage.value = 'This delivery has been cancelled';
    progressValue.value = 0.0;
    _stopPolling();
  }

  /// Handle unknown status
  void _handleUnknownStatus(String status) {
    currentStatus.value = status;
    statusMessage.value = 'Processing your request...';
    subStatusMessage.value = 'Please wait while we process your delivery';
    progressValue.value = 0.1;
  }

  /// Start polling for updates
  void _startPolling(int deliveryId) {
    _stopPolling(); // Stop any existing polling

    isPolling.value = true;
    _pollingTimer = Timer.periodic(Duration(seconds: 10), (timer) async {
      try {
        await _fetchDeliveryStatus(deliveryId);
      } catch (e) {
        print('❌ Polling error: $e');
        // Continue polling even if there's an error
      }
    });

    print('🔄 Started polling for delivery updates');
  }

  /// Stop polling
  void _stopPolling() {
    _pollingTimer?.cancel();
    _pollingTimer = null;
    isPolling.value = false;
    print('🛑 Stopped polling for delivery updates');
  }

  /// Get delivery tracking URL for sharing
  String getTrackingUrl(int deliveryId) {
    return '$baseUrl/deliveries/track/$deliveryId';
  }

  /// Check if delivery is completed
  bool get isCompleted {
    final status = currentStatus.value.toLowerCase();
    return status == 'delivered' || status == 'completed';
  }

  /// Check if delivery is cancelled
  bool get isCancelled {
    final status = currentStatus.value.toLowerCase();
    return status == 'cancelled' || status == 'canceled';
  }

  /// Check if driver is assigned
  bool get isDriverAssigned {
    final status = currentStatus.value.toLowerCase();
    return status == 'assigned' ||
        status == 'accepted' ||
        status == 'picked_up' ||
        status == 'pickedup' ||
        status == 'in_transit' ||
        status == 'in-transit' ||
        status == 'intransit' ||
        status == 'delivered' ||
        status == 'completed' ||
        driverData.isNotEmpty ||
        deliveryData['driver_id'] != null;
  }

  /// Get driver ID from driver data
  String? get driverId => driverData['id']?.toString();

  /// Get delivery ID from delivery data
  String? get deliveryId => deliveryData['id']?.toString();

  /// Fetch driver details using driver ID
  Future<void> _fetchDriverDetails(String driverId) async {
    try {
      print('🔍 Fetching driver details for ID: $driverId');

      final driverResponse = await http.get(
        Uri.parse('$baseUrl/drivers/$driverId'),
        headers: await _getHeaders(),
      );

      if (driverResponse.statusCode == 200) {
        final driverData =
            jsonDecode(driverResponse.body) as Map<String, dynamic>;
        final driver =
            (driverData['driver'] as Map<String, dynamic>?) ?? driverData;

        // Update driver information - match backend format
        driverName.value = driver['full_name'] ??
            '${driver['first_name'] ?? ''} ${driver['last_name'] ?? ''}'
                .trim() ??
            'Driver';
        // Backend returns phone in 'phone' field (mapped from phone_number)
        driverPhone.value = driver['phone']?.toString() ?? 
                            driver['phone_number']?.toString() ?? '';
        // Backend returns rating as float
        driverRating.value = driver['rating']?.toString() ?? '5.0';
        estimatedArrival.value = driver['estimated_arrival'] ?? '5-10 minutes';

        // Update driver data with complete information
        this.driverData.value = driver;

        print('✅ Driver details fetched successfully');
        print('👤 Driver: ${driverName.value}');
        print(
            '📞 Phone: ${driverPhone.value.isNotEmpty ? "Available" : "Not provided"}');
        print('⭐ Rating: ${driverRating.value}');
      } else {
        print(
            '⚠️ Failed to fetch driver details: ${driverResponse.statusCode}');
        print('⚠️ Response body: ${driverResponse.body}');
      }
    } catch (e) {
      print('❌ Error fetching driver details: $e');
    }
  }

  /// Get headers for API requests
  Future<Map<String, String>> _getHeaders() async {
    final token = await FirebaseAuth.instance.currentUser?.getIdToken();

    print(
        '🔐 Customer Tracking - Token retrieved: ${token != null ? "Present" : "Missing"}');
    if (token != null) {
      print(
          '🔐 Customer Tracking - Token preview: ${token.substring(0, 20)}...');
    }

    return {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }
}
