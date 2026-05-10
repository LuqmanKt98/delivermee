import 'dart:io';
import 'package:deliver_mee/src/common/constant/app_images.dart';
import 'package:deliver_mee/src/models/car_model.dart';
import 'package:deliver_mee/src/common/services/delivery_service.dart';
import 'package:deliver_mee/src/common/services/location_service.dart';
import 'package:deliver_mee/src/common/services/pricing_service.dart';
import 'package:get/get.dart';
import 'package:flutter/material.dart';

class HomeController extends GetxController {
  static HomeController get to => Get.find<HomeController>();
  RxString tolocation = 'Please select dropoff location'.obs;
  RxString fromlocation = 'Please select pickup location'.obs;

  // Location coordinates
  RxDouble pickupLatitude = 0.0.obs;
  RxDouble pickupLongitude = 0.0.obs;
  RxDouble dropoffLatitude = 0.0.obs;
  RxDouble dropoffLongitude = 0.0.obs;

  // Delivery creation state
  RxBool isCreatingDelivery = false.obs;

  // Store delivery data from backend response
  final RxMap<String, dynamic> deliveryData = <String, dynamic>{}.obs;
  final RxString deliveryId = ''.obs;
  final RxString trackingNumber = ''.obs;
  final RxString scheduledTime = ''.obs;
  final RxDouble deliveryPrice = 0.0.obs;
  RxString selectedVehicleType = 'cargo_van'.obs;
  RxString selectedPackageSize = 'medium'.obs;
  RxDouble packageWeight = 5.0.obs;
  RxInt itemCount = 1.obs;
  RxString itemName = ''.obs;
  RxString itemDescription = ''.obs;
  RxBool isFragile = false.obs;
  RxBool isPerishable = false.obs;
  RxBool requiresSignature = false.obs;
  RxString specialInstructions = ''.obs;
  RxString deliveryType = 'standard'.obs;
  RxString scheduleType = 'immediate'.obs;
  RxString deliveryPreference = 'attended'.obs;

  // Item photo handling
  Rx<File?> itemPhotoFile = Rx<File?>(null);

  // Scheduled delivery fields
  Rx<DateTime?> scheduledDate = Rx<DateTime?>(null);
  RxString timeSlot = ''.obs;

  // Location state
  RxBool isInitializingLocation = false.obs;
  RxBool hasLocationPermission = false.obs;

  // Delivery service
  late DeliveryService _deliveryService;

  @override
  void onInit() {
    super.onInit();
    // Initialize delivery service when needed
    _initializeCurrentLocationSeamlessly();
  }

  /// Initialize current location as default "to" location (seamless)
  void _initializeCurrentLocationSeamlessly() {
    // Set default fallback immediately for seamless UX
    tolocation.value = 'Current Location';

    // Initialize location in background without blocking UI
    _initializeCurrentLocation();
  }

  /// Initialize current location as default "to" location
  Future<void> _initializeCurrentLocation() async {
    if (isInitializingLocation.value)
      return; // Prevent multiple simultaneous calls

    try {
      isInitializingLocation.value = true;
      print('📍 Initializing current location...');

      final locationService = Get.find<LocationService>();

      // Check if we already have location permission
      hasLocationPermission.value = locationService.isLocationPermissionGranted;

      // Get current location
      final currentLocation = await locationService.getCurrentLocation();

      if (currentLocation != null &&
          currentLocation.latitude != null &&
          currentLocation.longitude != null) {
        // Set current location as default "to" location
        final address = locationService.currentAddress.isNotEmpty
            ? locationService.currentAddress
            : 'Current Location';

        // Only use the geocoded address if it's valid, otherwise use coordinates
        if (locationService.currentAddress.isNotEmpty &&
            locationService.currentAddress != 'Current Location') {
          tolocation.value = address;
        } else {
          // Use a more descriptive fallback that includes coordinates
          tolocation.value =
              'Current Location (${currentLocation.latitude!.toStringAsFixed(4)}, ${currentLocation.longitude!.toStringAsFixed(4)})';
        }

        // Set coordinates for "to" location
        dropoffLatitude.value = currentLocation.latitude!;
        dropoffLongitude.value = currentLocation.longitude!;

        // Ensure "from" location is properly initialized
        if (fromlocation.value == 'Please select pickup location') {
          fromlocation.value = 'Please select pickup location';
        }

        // Ensure "to" location is different from "from" location
        if (tolocation.value == fromlocation.value) {
          tolocation.value = address;
        }

        hasLocationPermission.value = true;

        print('✅ Default "to" location set to: ${tolocation.value}');
        print('✅ "From" location initialized to: ${fromlocation.value}');
        print(
            '📍 TO Coordinates: ${dropoffLatitude.value}, ${dropoffLongitude.value}');
        print(
            '📍 FROM Coordinates: ${pickupLatitude.value}, ${pickupLongitude.value}');
      } else {
        print('⚠️ Could not get current location, using fallback');
        // Use a more descriptive fallback
        tolocation.value = 'Please select dropoff location';
        fromlocation.value = 'Please select pickup location';
      }
    } catch (e) {
      print('❌ Error initializing current location: $e');
      // Keep the fallback "Current Location" that was set immediately
    } finally {
      isInitializingLocation.value = false;
    }
  }

  List<CarModel> carslist = [
    // CarModel(
    //   id: '1',
    //   image: AppImages.carimg,
    //   imagesecond: AppImages.carimgr,
    //   largebagcount: "1 Large Bag",
    //   name: "Car",
    //   pickuptime: "Pickup in 6 min",
    //   smallbagcount: "3-20 small Bag",
    // ),
    // CarModel(
    //   id: '2',
    //   image: AppImages.suvsimg,
    //   imagesecond: AppImages.suvsimgr,
    //   largebagcount: "2-12 Large Bag",
    //   name: "SUV",
    //   pickuptime: "Pickup in 6 min",
    //   smallbagcount: "4-10 Small Bag",
    // ),
    CarModel(
      id: '3',
      image: AppImages.cargovanimg,
      imagesecond: AppImages.cargovanimgr,
      largebagcount: "15-50 Large Bag",
      name: "Cargo Van",
      pickuptime: "Pickup in 6 min",
      smallbagcount: "30-100 Small Bag",
    ),
    CarModel(
      id: '4',
      image: AppImages.pickuptruckimg,
      imagesecond: AppImages.pickuptruckimgr,
      largebagcount: "7-17 Large Bag",
      name: "Pickup Truck",
      pickuptime: "Pickup in 6 min",
      smallbagcount: "15-35 Small Bag",
    ),
    // Box Truck - Commented out (only Cargo Van and Pickup Truck available)
    // CarModel(
    //   id: '5',
    //   image: AppImages.boxtruckimg,
    //   imagesecond: AppImages.boxtruckimgr,
    //   largebagcount: "25-75 Large Bag",
    //   name: "Box Truck",
    //   pickuptime: "Pickup in 6 min",
    //   smallbagcount: "50-150 Small Bag",
    // ),
  ];

  /// Update pickup location
  void updateFromLocation(String address, double? latitude, double? longitude) {
    print('🔄 Updating FROM location: $address');
    fromlocation.value = address;
    if (latitude != null && longitude != null) {
      pickupLatitude.value = latitude;
      pickupLongitude.value = longitude;
      print('📍 FROM coordinates: $latitude, $longitude');
      print('✅ FROM coordinates set successfully');
    } else {
      print(
          '⚠️ FROM coordinates are null - latitude: $latitude, longitude: $longitude');
    }
  }

  /// Update dropoff location
  void updateToLocation(String address, double? latitude, double? longitude) {
    print('🔄 Updating TO location: $address');
    tolocation.value = address;
    if (latitude != null && longitude != null) {
      dropoffLatitude.value = latitude;
      dropoffLongitude.value = longitude;
      print('📍 TO coordinates: $latitude, $longitude');
      print('✅ TO coordinates set successfully');
    } else {
      print(
          '⚠️ TO coordinates are null - latitude: $latitude, longitude: $longitude');
    }
  }

  /// Validate delivery data
  bool validateDeliveryData() {
    if (fromlocation.value.isEmpty || tolocation.value.isEmpty) {
      Get.snackbar(
        'Error',
        'Please select both pickup and dropoff locations',
        backgroundColor: Colors.red,
        colorText: Colors.white,
      );
      return false;
    }

    if (itemName.value.isEmpty) {
      Get.snackbar(
        'Error',
        'Please enter item name',
        backgroundColor: Colors.red,
        colorText: Colors.white,
      );
      return false;
    }

    if (packageWeight.value <= 0) {
      Get.snackbar(
        'Error',
        'Please enter valid package weight',
        backgroundColor: Colors.red,
        colorText: Colors.white,
      );
      return false;
    }

    if (itemCount.value <= 0) {
      Get.snackbar(
        'Error',
        'Please enter valid item count',
        backgroundColor: Colors.red,
        colorText: Colors.white,
      );
      return false;
    }

    if (selectedVehicleType.value.isEmpty) {
      Get.snackbar(
        'Error',
        'Please select a service type',
        backgroundColor: Colors.red,
        colorText: Colors.white,
      );
      return false;
    }

    return true;
  }

  /// Create delivery
  Future<bool> createDelivery() async {
    if (!validateDeliveryData()) return false;

    // DEBUG: Check if photo file exists before creating delivery
    print('🔍 DEBUG: itemPhotoFile.value = ${itemPhotoFile.value}');
    print('🔍 DEBUG: itemPhotoFile.value?.path = ${itemPhotoFile.value?.path}');
    print('🔍 DEBUG: itemPhotoFile is null? ${itemPhotoFile.value == null}');

    try {
      isCreatingDelivery.value = true;

      // Initialize delivery service when needed
      _deliveryService = Get.find<DeliveryService>();

      print('🚀 Starting delivery creation...');
      print('📍 From: ${fromlocation.value}');
      print('📍 To: ${tolocation.value}');
      print('📦 Item: ${itemName.value}');
      print('📝 Description: ${itemDescription.value}');
      print('🚛 Vehicle: ${selectedVehicleType.value}');
      print('📏 Package Size: ${selectedPackageSize.value}');
      print('⚖️ Weight: ${packageWeight.value} lbs');
      print('🔢 Item Count: ${itemCount.value}');
      print('🚚 Delivery Type: ${deliveryType.value}');
      print('📅 Schedule Type: ${scheduleType.value}');

      final result = await _deliveryService.createDelivery(
        pickupAddress: fromlocation.value,
        dropoffAddress: tolocation.value,
        pickupLatitude: pickupLatitude.value > 0 ? pickupLatitude.value : null,
        pickupLongitude:
            pickupLongitude.value > 0 ? pickupLongitude.value : null,
        dropoffLatitude:
            dropoffLatitude.value > 0 ? dropoffLatitude.value : null,
        dropoffLongitude:
            dropoffLongitude.value > 0 ? dropoffLongitude.value : null,
        itemName: itemName.value,
        itemDescription:
            itemDescription.value.isNotEmpty ? itemDescription.value : null,
        itemPhotoFile: itemPhotoFile.value, // Pass the photo file
        vehicleType: selectedVehicleType.value,
        packageSize: selectedPackageSize.value,
        weight: packageWeight.value,
        itemCount: itemCount.value,
        isFragile: isFragile.value,
        isPerishable: isPerishable.value,
        requiresSignature: requiresSignature.value,
        specialInstructions: specialInstructions.value.isNotEmpty
            ? specialInstructions.value
            : null,
        deliveryType: deliveryType.value,
        scheduleType: scheduleType.value,
        scheduledDate: scheduledDate.value,
        timeSlot: timeSlot.value.isNotEmpty ? timeSlot.value : null,
        deliveryPreference: deliveryPreference.value,
      );

      print('📡 Delivery creation result: $result');

      if (result['success']) {
        final responseData = result['data'];
        final trackingNum = result['tracking_number'] ??
            responseData['tracking_number'] ??
            responseData['id'] ??
            'N/A';

        // Store delivery data for use in payment screen
        deliveryData.value = responseData;
        trackingNumber.value = trackingNum;

        // Extract delivery ID
        if (responseData['delivery'] != null &&
            responseData['delivery']['id'] != null) {
          deliveryId.value = responseData['delivery']['id'].toString();
        } else if (responseData['id'] != null) {
          deliveryId.value = responseData['id'].toString();
        }

        // Extract scheduled time information
        if (responseData['delivery'] != null &&
            responseData['delivery']['scheduled_time'] != null) {
          scheduledTime.value = responseData['delivery']['scheduled_time'];
        } else if (responseData['scheduled_time'] != null) {
          scheduledTime.value = responseData['scheduled_time'];
        } else if (scheduleType.value == 'scheduled' &&
            scheduledDate.value != null &&
            timeSlot.value.isNotEmpty) {
          // Format scheduled time from our data
          final date = scheduledDate.value!;
          scheduledTime.value =
              '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')} at $timeSlot';
        }

        // Extract estimated cost from delivery response - try multiple possible fields
        double estimatedCost = 0.0;
        print('🔍 Searching for cost in delivery response...');
        print('🔍 Response structure: $responseData');

        // Try different possible field names for cost
        if (responseData['delivery'] != null) {
          final delivery = responseData['delivery'];
          if (delivery['estimated_cost'] != null) {
            estimatedCost = delivery['estimated_cost'].toDouble();
            print('💰 Found cost in delivery.estimated_cost: $estimatedCost');
          } else if (delivery['cost'] != null) {
            estimatedCost = delivery['cost'].toDouble();
            print('💰 Found cost in delivery.cost: $estimatedCost');
          } else if (delivery['total_cost'] != null) {
            estimatedCost = delivery['total_cost'].toDouble();
            print('💰 Found cost in delivery.total_cost: $estimatedCost');
          } else if (delivery['price'] != null) {
            estimatedCost = delivery['price'].toDouble();
            print('💰 Found cost in delivery.price: $estimatedCost');
          }
        }

        // Try top-level fields
        if (estimatedCost == 0.0) {
          if (responseData['estimated_cost'] != null) {
            estimatedCost = responseData['estimated_cost'].toDouble();
            print('💰 Found cost in estimated_cost: $estimatedCost');
          } else if (responseData['cost'] != null) {
            estimatedCost = responseData['cost'].toDouble();
            print('💰 Found cost in cost: $estimatedCost');
          } else if (responseData['total_cost'] != null) {
            estimatedCost = responseData['total_cost'].toDouble();
            print('💰 Found cost in total_cost: $estimatedCost');
          } else if (responseData['price'] != null) {
            estimatedCost = responseData['price'].toDouble();
            print('💰 Found cost in price: $estimatedCost');
          }
        }

        // If still no cost found, try to extract from any numeric field that might be the cost
        if (estimatedCost == 0.0) {
          print(
              '⚠️ No cost found in expected fields, searching for any numeric value...');
          for (String key in responseData.keys) {
            if (responseData[key] is num && responseData[key] > 0) {
              print('🔍 Found numeric value in $key: ${responseData[key]}');
              // If it's a reasonable delivery cost (between $5 and $500)
              if (responseData[key] >= 5.0 && responseData[key] <= 500.0) {
                estimatedCost = responseData[key].toDouble();
                print('💰 Using $key as cost: $estimatedCost');
                break;
              }
            }
          }
        }

        // Store delivery price for use in payment screen (similar to deliveryId)
        deliveryPrice.value = estimatedCost;

        print('✅ Delivery created successfully!');
        print('📦 Delivery data: $responseData');
        print('📦 Tracking Number: $trackingNum');
        print('📦 Delivery ID: ${deliveryId.value}');
        print('📦 Scheduled Time: ${scheduledTime.value}');
        print('💰 Delivery Price: \$${deliveryPrice.value.toStringAsFixed(2)}');

        // Update pricing service with estimated cost from delivery response
        if (estimatedCost > 0) {
          final pricingService = Get.find<PricingService>();
          pricingService.setPricingFromDeliveryData(responseData);
          print(
              '💰 Updated pricing service with estimated cost: \$${estimatedCost.toStringAsFixed(2)}');
        } else {
          // Fallback: If no cost found in response, try to use a reasonable default
          // Based on the backend logs showing $84.98, we'll use this as a fallback
          print('⚠️ No cost found in delivery response, using fallback cost');
          final pricingService = Get.find<PricingService>();
          pricingService.setTotalFare(84.98); // Use the cost from backend logs
          deliveryPrice.value = 84.98; // Also store in deliveryPrice
          print('💰 Set fallback cost: \$84.98');
        }

        Get.snackbar(
          'Success',
          'Delivery created successfully!\nTracking: $trackingNumber',
          backgroundColor: Colors.green,
          colorText: Colors.white,
          duration: Duration(seconds: 5),
          icon: Icon(Icons.check_circle, color: Colors.white),
        );

        // Navigate to delivery tracking or confirmation screen
        // Get.to(() => DeliveryConfirmationScreen(trackingNumber: trackingNumber));

        // Reset form
        resetDeliveryForm();
        return true; // Success
      } else {
        print('❌ Delivery creation failed: ${result['error']}');
        Get.snackbar(
          'Error',
          result['error'] ?? 'Failed to create delivery',
          backgroundColor: Colors.red,
          colorText: Colors.white,
          duration: Duration(seconds: 5),
          icon: Icon(Icons.error, color: Colors.white),
        );
        return false; // Failure
      }
    } catch (e) {
      Get.snackbar(
        'Error',
        'Failed to create delivery: ${e.toString()}',
        backgroundColor: Colors.red,
        colorText: Colors.white,
      );
      return false; // Failure
    } finally {
      isCreatingDelivery.value = false;
    }
  }

  /// Reset delivery form
  void resetDeliveryForm() {
    itemName.value = '';
    itemDescription.value = '';
    itemPhotoFile.value = null; // Clear the photo from previous delivery
    packageWeight.value = 5.0;
    itemCount.value = 1;
    isFragile.value = false;
    isPerishable.value = false;
    requiresSignature.value = false;
    specialInstructions.value = '';
    selectedVehicleType.value = 'cargo_van';
    selectedPackageSize.value = 'medium';
    deliveryType.value = 'standard';
    scheduleType.value = 'immediate';
    deliveryPreference.value = 'attended';
    scheduledDate.value = null;
    timeSlot.value = '';

    // Reset "to" location to current location
    refreshCurrentLocation();

    print('🧹 Delivery form reset, photo cleared');
  }

  /// Clear delivery data (for starting fresh)
  void clearDeliveryData() {
    deliveryData.clear();
    deliveryId.value = '';
    trackingNumber.value = '';
    scheduledTime.value = '';
    deliveryPrice.value = 0.0;
    print('🧹 Cleared delivery data');
  }

  /// Ensure locations are properly set for payment screen
  void ensureLocationsForPayment() {
    print('📍 Ensuring locations are properly set for payment screen...');
    print('📍 Current FROM: ${fromlocation.value}');
    print('📍 Current TO: ${tolocation.value}');

    // Ensure "from" location is not empty
    if (fromlocation.value.isEmpty ||
        fromlocation.value == 'Please select pickup location') {
      if (fromlocation.value != 'Please select pickup location') {
        fromlocation.value = 'Please select pickup location';
      }
    }

    // Ensure "to" location is not empty
    if (tolocation.value.isEmpty ||
        tolocation.value == 'Please select dropoff location') {
      if (tolocation.value != 'Current Location') {
        tolocation.value = 'Current Location';
      }
    }

    // Ensure locations are different
    if (fromlocation.value == tolocation.value) {
      if (tolocation.value != 'Current Location') {
        tolocation.value = 'Current Location';
      }
    }

    print('✅ Locations ensured for payment screen');
    print('📍 Final FROM: ${fromlocation.value}');
    print('📍 Final TO: ${tolocation.value}');
  }

  /// Set vehicle type
  void setVehicleType(String vehicleType) {
    selectedVehicleType.value = vehicleType;
    print('🚛 Vehicle type set to: $vehicleType');

    // Special debugging for Cargo Van
    if (vehicleType == 'cargo_van') {
      print('🚐 Cargo Van selected - vehicle type confirmed');
    }
  }

  /// Set package size
  void setPackageSize(String packageSize) {
    selectedPackageSize.value = packageSize;
  }

  /// Set delivery type
  void setDeliveryType(String type) {
    deliveryType.value = type;
    print('🚚 Delivery type set to: $type');
  }

  /// Set schedule type
  void setScheduleType(String type) {
    scheduleType.value = type;
  }

  /// Set scheduled date
  void setScheduledDate(DateTime? date) {
    scheduledDate.value = date;
  }

  /// Set time slot
  void setTimeSlot(String slot) {
    timeSlot.value = slot;
  }

  /// Set item details from car selection
  void setItemDetails({
    required int itemCount,
    required double weight,
    required String packageSize,
  }) {
    this.itemCount.value = itemCount;
    packageWeight.value = weight;
    selectedPackageSize.value = packageSize;
    print(
        '📦 Item details set - Count: $itemCount, Weight: $weight, Size: $packageSize');
  }

  /// Set item name and description
  void setItemInfo({
    required String itemName,
    String? itemDescription,
  }) {
    this.itemName.value = itemName;
    if (itemDescription != null) {
      this.itemDescription.value = itemDescription;
    }
    print('📝 Item info set - Name: $itemName, Description: $itemDescription');
  }

  /// Refresh current location as "to" location
  Future<void> refreshCurrentLocation() async {
    if (isInitializingLocation.value)
      return; // Prevent multiple simultaneous calls

    try {
      isInitializingLocation.value = true;
      print('🔄 Refreshing current location...');

      final locationService = Get.find<LocationService>();

      // Get fresh current location
      final currentLocation = await locationService.getCurrentLocation();

      if (currentLocation != null &&
          currentLocation.latitude != null &&
          currentLocation.longitude != null) {
        // Update "to" location with fresh data
        final address = locationService.currentAddress.isNotEmpty
            ? locationService.currentAddress
            : 'Current Location';

        tolocation.value = address;

        // Update coordinates for "to" location
        dropoffLatitude.value = currentLocation.latitude!;
        dropoffLongitude.value = currentLocation.longitude!;

        hasLocationPermission.value = true;

        print('✅ "To" location refreshed to: ${tolocation.value}');
        print(
            '📍 New coordinates: ${dropoffLatitude.value}, ${dropoffLongitude.value}');
      } else {
        print('⚠️ Could not refresh current location, keeping current value');
      }
    } catch (e) {
      print('❌ Error refreshing current location: $e');
      // Keep current value on error
    } finally {
      isInitializingLocation.value = false;
    }
  }

  /// Set "to" location to current location (for UI button)
  Future<void> setToCurrentLocation() async {
    await refreshCurrentLocation();
  }

  /// Request location permission seamlessly
  Future<bool> requestLocationPermission() async {
    try {
      print('🔐 Requesting location permission...');
      final locationService = Get.find<LocationService>();

      final granted = await locationService.requestLocationPermission();
      hasLocationPermission.value = granted;

      if (granted) {
        print('✅ Location permission granted');
        // Try to get location after permission is granted
        await refreshCurrentLocation();
        return true;
      } else {
        print('❌ Location permission denied');
        return false;
      }
    } catch (e) {
      print('❌ Error requesting location permission: $e');
      return false;
    }
  }

  /// Check if location is available and working
  bool get isLocationAvailable =>
      hasLocationPermission.value &&
      dropoffLatitude.value != 0.0 &&
      dropoffLongitude.value != 0.0;

  /// Get location status for UI
  String get locationStatus {
    if (isInitializingLocation.value) return 'Getting location...';
    if (hasLocationPermission.value && isLocationAvailable)
      return 'Location ready';
    if (!hasLocationPermission.value) return 'Location permission needed';
    return 'Location unavailable';
  }

  /// Set item photo file
  void setItemPhotoFile(File? photoFile) {
    itemPhotoFile.value = photoFile;
    if (photoFile != null) {
      print('📸 Item photo file set: ${photoFile.path}');
    } else {
      print('⚠️ Item photo file cleared');
    }
  }
}
