import 'dart:convert';
import 'dart:math' as math;
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:geocoding/geocoding.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../constant/api_config.dart';

class DeliveryService extends GetxService {
  static DeliveryService get to => Get.find<DeliveryService>();

  // Using centralized API configuration
  String get baseUrl => ApiConfig.baseUrl;
  String get apiBaseUrl => baseUrl;

  // Headers for API requests with authentication
  Future<Map<String, String>> _getHeaders() async {
    final token = await FirebaseAuth.instance.currentUser?.getIdToken();

    return {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  /// Get customer ID from stored user data
  Future<int> _getCustomerId() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final customerId = prefs.getInt('customer_id');

      if (customerId != null) {
        print('👤 Customer ID found: $customerId');
        return customerId;
      } else {
        print('⚠️ No customer ID found, using default: 1');
        return 1; // Default customer ID for testing
      }
    } catch (e) {
      print('❌ Error getting customer ID: $e, using default: 1');
      return 1; // Default customer ID for testing
    }
  }

  /// Map vehicle type to backend format
  String _mapVehicleType(String vehicleType) {
    print('🚛 Mapping vehicle type: "$vehicleType"');
    final mapping = {
      'car': 'car',
      'suv': 'suv',
      'pickup_truck': 'pickup_truck',
      'cargo_van': 'cargo_van',
      'box_truck': 'box_truck',
      'sedan': 'car'
    };
    final mappedType = mapping[vehicleType.toLowerCase()] ?? 'cargo_van';
    print('🚛 Mapped vehicle type: "$mappedType"');

    // Special debugging for all vehicle types
    if (vehicleType.toLowerCase() == 'cargo_van') {
      print('🚐 Cargo Van detected - mapped to: $mappedType');
      print('🚐 Input: "$vehicleType" -> Output: "$mappedType"');
    } else if (vehicleType.toLowerCase() == 'pickup_truck') {
      print('🚛 Pickup Truck detected - mapped to: $mappedType');
      print('🚛 Input: "$vehicleType" -> Output: "$mappedType"');
    } else if (vehicleType.toLowerCase() == 'box_truck') {
      print('📦 Box Truck detected - mapped to: $mappedType');
      print('📦 Input: "$vehicleType" -> Output: "$mappedType"');
    }

    return mappedType;
  }

  /// Map delivery type to backend format
  String _mapDeliveryType(String deliveryType) {
    final mapping = {
      'pickup': 'standard', // Map pickup to standard
      'box': 'standard', // Map box to standard
      'cargo': 'standard', // Map cargo to standard
      'standard': 'standard',
      'express': 'express',
      'same_day': 'same_day'
    };
    return mapping[deliveryType.toLowerCase()] ?? 'standard';
  }

  /// Calculate distance between two coordinates using Haversine formula
  double _calculateDistance(
      double lat1, double lon1, double lat2, double lon2) {
    const double earthRadius = 6371; // Earth's radius in kilometers

    final double dLat = _degreesToRadians(lat2 - lat1);
    final double dLon = _degreesToRadians(lon2 - lon1);

    final double a = (math.sin(dLat / 2) * math.sin(dLat / 2)) +
        (math.cos(_degreesToRadians(lat1)) *
            math.cos(_degreesToRadians(lat2)) *
            math.sin(dLon / 2) *
            math.sin(dLon / 2));

    final double c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a));
    final double distance = earthRadius * c; // Distance in kilometers

    print('📏 Distance calculated: ${distance.toStringAsFixed(2)} km');
    return distance;
  }

  /// Convert degrees to radians
  double _degreesToRadians(double degrees) {
    return degrees * (math.pi / 180);
  }

  /// Get coordinates from address using geocoding
  Future<Map<String, double>?> _getCoordinatesFromAddress(
      String address) async {
    try {
      print('🌍 Geocoding address: $address');
      final locations = await locationFromAddress(address);

      if (locations.isNotEmpty) {
        final location = locations.first;
        print(
            '✅ Coordinates found: ${location.latitude}, ${location.longitude}');
        return {
          'latitude': location.latitude,
          'longitude': location.longitude,
        };
      } else {
        print('❌ No coordinates found for address: $address');
        return null;
      }
    } catch (e) {
      print('❌ Error geocoding address: $e');
      return null;
    }
  }

  /// Map package size to backend format
  String _mapPackageSize(String packageSize) {
    final mapping = {
      'small': 'small',
      'medium': 'medium',
      'large': 'large',
      'xl': 'extra_large', // Map XL to extra_large as per backend enum
      'extra_large': 'extra_large',
      'oversized': 'huge', // Map oversized to huge as per backend enum
      'huge': 'huge',
    };
    return mapping[packageSize.toLowerCase()] ?? 'medium';
  }

  /// Create a new delivery
  Future<Map<String, dynamic>> createDelivery({
    required String pickupAddress,
    required String dropoffAddress,
    double? pickupLatitude,
    double? pickupLongitude,
    double? dropoffLatitude,
    double? dropoffLongitude,
    required String itemName,
    String? itemDescription,
    String? itemPhotoUrl,
    File? itemPhotoFile, // New parameter for photo file upload
    required String vehicleType,
    String? packageSize,
    String? packageType,
    double? width,
    double? height,
    double? length,
    required double weight,
    int itemCount = 1,
    bool isFragile = false,
    bool isPerishable = false,
    bool requiresSignature = false,
    String? specialInstructions,
    String deliveryType = 'standard',
    required String scheduleType,
    DateTime? scheduledDate,
    String? timeSlot,
    String deliveryPreference = 'attended',
  }) async {
    try {
      final url = Uri.parse('$apiBaseUrl/deliveries/create');

      final mappedVehicleType = _mapVehicleType(vehicleType);
      print('🔍 DEBUG: Original vehicle type: "$vehicleType"');
      print('🔍 DEBUG: Mapped vehicle type: "$mappedVehicleType"');

      final requestBody = {
        'customer_id': await _getCustomerId(), // Add customer_id
        'pickup_address': pickupAddress,
        'dropoff_address': dropoffAddress,
        'item_name': itemName,
        'vehicle_type': mappedVehicleType,
        'weight': weight,
        'schedule_type': scheduleType,
        'delivery_preference': deliveryPreference,
        'item_count': itemCount,
        'delivery_type': _mapDeliveryType(deliveryType),
      };

      // Calculate estimated distance if coordinates are available
      double? estimatedDistance;

      if (pickupLatitude != null &&
          pickupLongitude != null &&
          dropoffLatitude != null &&
          dropoffLongitude != null) {
        // Use provided coordinates
        estimatedDistance = _calculateDistance(
          pickupLatitude,
          pickupLongitude,
          dropoffLatitude,
          dropoffLongitude,
        );
        print(
            '📏 Distance calculated from provided coordinates: ${estimatedDistance.toStringAsFixed(2)} km');
      } else {
        // Try to get coordinates from addresses as fallback
        print('⚠️ No coordinates provided, attempting to geocode addresses...');

        try {
          final pickupCoords = await _getCoordinatesFromAddress(pickupAddress);
          final dropoffCoords =
              await _getCoordinatesFromAddress(dropoffAddress);

          if (pickupCoords != null && dropoffCoords != null) {
            estimatedDistance = _calculateDistance(
              pickupCoords['latitude']!,
              pickupCoords['longitude']!,
              dropoffCoords['latitude']!,
              dropoffCoords['longitude']!,
            );
            print(
                '📏 Distance calculated from geocoded addresses: ${estimatedDistance.toStringAsFixed(2)} km');
          } else {
            print(
                '❌ Could not get coordinates from addresses, skipping distance calculation');
          }
        } catch (e) {
          print('❌ Error geocoding addresses for distance calculation: $e');
        }
      }

      // Add distance to request body if calculated
      if (estimatedDistance != null) {
        requestBody['estimated_distance_km'] = estimatedDistance;
        print(
            '📏 Added estimated distance to request: ${estimatedDistance.toStringAsFixed(2)} km');
      }

      print('📦 Delivery request body: ${jsonEncode(requestBody)}');
      print('🚛 Vehicle type in request: "${requestBody['vehicle_type']}"');

      // Add optional fields if provided
      if (pickupLatitude != null && pickupLongitude != null) {
        requestBody['pickup_latitude'] = pickupLatitude;
        requestBody['pickup_longitude'] = pickupLongitude;
      }

      if (dropoffLatitude != null && dropoffLongitude != null) {
        requestBody['dropoff_latitude'] = dropoffLatitude;
        requestBody['dropoff_longitude'] = dropoffLongitude;
      }

      if (itemDescription != null)
        requestBody['item_description'] = itemDescription;
      if (itemPhotoUrl != null) requestBody['item_photo_url'] = itemPhotoUrl;
      if (packageSize != null)
        requestBody['package_size'] = _mapPackageSize(packageSize);
      if (packageType != null) requestBody['package_type'] = packageType;
      if (width != null) requestBody['width'] = width;
      if (height != null) requestBody['height'] = height;
      if (length != null) requestBody['length'] = length;
      if (isFragile) requestBody['is_fragile'] = isFragile;
      if (isPerishable) requestBody['is_perishable'] = isPerishable;
      if (requiresSignature)
        requestBody['requires_signature'] = requiresSignature;
      if (specialInstructions != null)
        requestBody['special_instructions'] = specialInstructions;
      if (scheduledDate != null)
        requestBody['scheduled_date'] =
            scheduledDate.toIso8601String().split('T')[0];
      if (timeSlot != null) {
        requestBody['time_slot'] = timeSlot;
        print('🔍 Setting time_slot in request body: $timeSlot');
      }

      // Validate required fields before sending
      if (pickupAddress.length < 5) {
        return {
          'success': false,
          'error': 'Pickup address must be at least 5 characters',
        };
      }

      if (dropoffAddress.length < 5) {
        return {
          'success': false,
          'error': 'Dropoff address must be at least 5 characters',
        };
      }

      // Check if we have coordinates for both locations
      bool hasPickupCoords = pickupLatitude != null && pickupLongitude != null;
      bool hasDropoffCoords =
          dropoffLatitude != null && dropoffLongitude != null;

      if (!hasPickupCoords) {
        print(
            '⚠️ No pickup coordinates provided, backend will geocode pickup address');
      }

      if (!hasDropoffCoords) {
        print(
            '⚠️ No dropoff coordinates provided, backend will geocode dropoff address');
      }

      if (weight <= 0) {
        return {
          'success': false,
          'error': 'Weight must be greater than 0 lbs',
        };
      }

      print('🚀 Creating delivery with data: ${jsonEncode(requestBody)}');
      print('🔗 API URL: $url');
      print('🚛 Original Vehicle Type: $vehicleType');
      print('🚛 Mapped Vehicle Type: ${_mapVehicleType(vehicleType)}');
      print('🚚 Delivery Type: ${_mapDeliveryType(deliveryType)}');
      print('🔍 Vehicle Type in Request Body: ${requestBody['vehicle_type']}');
      if (packageSize != null) {
        print(
            '📦 Package Size: $packageSize -> ${_mapPackageSize(packageSize)}');
      }

      final response = await http.post(
        url,
        headers: await _getHeaders(),
        body: jsonEncode(requestBody),
      );

      print(
          '📡 Delivery API Response: ${response.statusCode} - ${response.body}');

      if (response.statusCode == 200 || response.statusCode == 201) {
        try {
          final responseData = jsonDecode(response.body);
          final trackingNumber = responseData['tracking_number'] ??
              responseData['delivery']?['tracking_number'] ??
              'N/A';
          final deliveryId = responseData['delivery_id'] ??
              responseData['delivery']?['id'] ??
              responseData['id'];

          print('✅ Delivery created successfully!');
          print('📦 Tracking Number: $trackingNumber');
          print('📦 Delivery ID: $deliveryId (type: ${deliveryId.runtimeType})');
          print('📦 Full Response: $responseData');

          // Handle item photo upload if photo file is provided
          if (itemPhotoFile != null && deliveryId != null) {
            // Convert deliveryId to int if it's a string
            final int deliveryIdInt;
            if (deliveryId is String) {
              deliveryIdInt = int.tryParse(deliveryId) ?? 0;
              print('📦 Converted delivery ID from string to int: $deliveryIdInt');
            } else if (deliveryId is int) {
              deliveryIdInt = deliveryId;
            } else {
              print('❌ Invalid delivery ID type: ${deliveryId.runtimeType}');
              deliveryIdInt = 0;
            }

            if (deliveryIdInt > 0) {
              print('📸 Item photo file provided: ${itemPhotoFile.path}');
              print('📸 File exists: ${await itemPhotoFile.exists()}');
              print('📸 File size: ${await itemPhotoFile.length()} bytes');
              print('📸 Uploading item photo for delivery: $deliveryIdInt');

              final photoUploadResult = await uploadDeliveryItemPhoto(
                deliveryId: deliveryIdInt,
                photoFile: itemPhotoFile,
              );

              if (photoUploadResult['success']) {
                print('✅ Item photo uploaded successfully');
                responseData['item_photo_url'] =
                    photoUploadResult['item_photo_url'];
              } else {
                print(
                    '⚠️ Item photo upload failed: ${photoUploadResult['error']}');
                // Don't fail the entire delivery creation if photo upload fails
                responseData['photo_upload_error'] = photoUploadResult['error'];
              }
            } else {
              print('❌ Invalid delivery ID for photo upload: $deliveryIdInt');
            }
          } else {
            if (itemPhotoFile == null) {
              print('⚠️ No item photo file provided');
            }
            if (deliveryId == null) {
              print('⚠️ No delivery ID available');
            }
          }

          return {
            'success': true,
            'data': responseData,
            'tracking_number': trackingNumber,
            'delivery_id': deliveryId,
          };
        } catch (e) {
          print('❌ Error parsing success response: $e');
          return {
            'success': false,
            'error': 'Failed to parse server response: $e',
          };
        }
      } else {
        print('❌ Delivery creation failed with status: ${response.statusCode}');
        print('❌ Response body: ${response.body}');

        try {
          final errorData = jsonDecode(response.body);
          final errorMessage = errorData['error'] ??
              errorData['message'] ??
              'Failed to create delivery';
          print('❌ Server error: $errorMessage');

          // Handle specific geocoding errors
          if (errorMessage.toLowerCase().contains('geocode')) {
            return {
              'success': false,
              'error':
                  'Address not found. Please select a valid pickup and dropoff location.',
            };
          }

          return {
            'success': false,
            'error': errorMessage,
          };
        } catch (e) {
          print('❌ Error parsing error response: $e');
          return {
            'success': false,
            'error': 'Server error: ${response.statusCode} - ${response.body}',
          };
        }
      }
    } catch (e) {
      print('❌ Delivery creation error: $e');
      return {
        'success': false,
        'error': 'Network error: ${e.toString()}',
      };
    }
  }

  /// Get available time slots for a specific date
  Future<Map<String, dynamic>> getAvailableTimeSlots(DateTime date) async {
    try {
      final dateString = date.toIso8601String().split('T')[0];
      final url =
          Uri.parse('$apiBaseUrl/deliveries/available-slots/$dateString');

      final response = await http.get(url, headers: await _getHeaders());

      if (response.statusCode == 200) {
        final responseData = jsonDecode(response.body);
        return {
          'success': true,
          'data': responseData,
        };
      } else {
        final errorData = jsonDecode(response.body);
        return {
          'success': false,
          'error': errorData['error'] ?? 'Failed to get time slots',
        };
      }
    } catch (e) {
      return {
        'success': false,
        'error': 'Network error: ${e.toString()}',
      };
    }
  }

  /// Get user's deliveries
  Future<Map<String, dynamic>> getUserDeliveries({
    String? status,
    String? deliveryType,
    int limit = 20,
    int offset = 0,
  }) async {
    try {
      final queryParams = <String, String>{
        'limit': limit.toString(),
        'offset': offset.toString(),
      };

      if (status != null) queryParams['status'] = status;
      if (deliveryType != null) queryParams['delivery_type'] = deliveryType;

      final uri = Uri.parse('$apiBaseUrl/deliveries/').replace(
        queryParameters: queryParams,
      );

      print('📡 Fetching deliveries from: $uri');
      print('📡 Headers: ${await _getHeaders()}');

      final response = await http.get(uri, headers: await _getHeaders());

      print('📡 Response status: ${response.statusCode}');
      print('📡 Response body: ${response.body}');

      if (response.statusCode == 200) {
        final responseData = jsonDecode(response.body);
        return {
          'success': true,
          'data': responseData,
        };
      } else {
        try {
          final errorData = jsonDecode(response.body);
          print('❌ Error response: $errorData');
          return {
            'success': false,
            'error': errorData['error'] ?? 'Failed to get deliveries',
          };
        } catch (e) {
          print('❌ Failed to parse error response: $e');
          return {
            'success': false,
            'error': 'Server error: ${response.statusCode}',
          };
        }
      }
    } catch (e) {
      print('❌ Network error in getUserDeliveries: $e');
      return {
        'success': false,
        'error': 'Network error: ${e.toString()}',
      };
    }
  }

  /// Track delivery by tracking number
  Future<Map<String, dynamic>> trackDelivery(String trackingNumber) async {
    try {
      final url = Uri.parse('$apiBaseUrl/deliveries/track/$trackingNumber');

      final response = await http.get(url, headers: await _getHeaders());

      if (response.statusCode == 200) {
        final responseData = jsonDecode(response.body);
        return {
          'success': true,
          'data': responseData,
        };
      } else {
        final errorData = jsonDecode(response.body);
        return {
          'success': false,
          'error': errorData['error'] ?? 'Delivery not found',
        };
      }
    } catch (e) {
      return {
        'success': false,
        'error': 'Network error: ${e.toString()}',
      };
    }
  }

  /// Cancel delivery
  Future<Map<String, dynamic>> cancelDelivery(int deliveryId) async {
    try {
      final url = Uri.parse('$apiBaseUrl/deliveries/$deliveryId/cancel');

      final response = await http.post(url, headers: await _getHeaders());

      if (response.statusCode == 200) {
        final responseData = jsonDecode(response.body);
        return {
          'success': true,
          'data': responseData,
        };
      } else {
        final errorData = jsonDecode(response.body);
        return {
          'success': false,
          'error': errorData['error'] ?? 'Failed to cancel delivery',
        };
      }
    } catch (e) {
      return {
        'success': false,
        'error': 'Network error: ${e.toString()}',
      };
    }
  }

  /// Get signed upload URL for delivery item photo (public endpoint)
  Future<Map<String, dynamic>> getItemPhotoUploadUrl({
    required int deliveryId,
    required String filename,
    required String contentType,
  }) async {
    try {
      final url =
          Uri.parse('$apiBaseUrl/deliveries/item-photo/upload-url/public');

      final requestBody = {
        'delivery_id': deliveryId,
        'filename': filename,
        'content_type': contentType,
      };

      print('📸 Getting item photo upload URL for delivery: $deliveryId');
      print('📸 Request body: ${jsonEncode(requestBody)}');

      final response = await http.post(
        url,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: jsonEncode(requestBody),
      );

      print(
          '📸 Upload URL response: ${response.statusCode} - ${response.body}');

      if (response.statusCode == 200) {
        final responseData = jsonDecode(response.body);
        return {
          'success': true,
          'data': responseData,
          'upload_url': responseData['upload_url'],
          'object_key': responseData['object_key'],
          'expires_in': responseData['expires_in'],
          'item_photo_url': responseData['item_photo_url'],
        };
      } else {
        final errorData = jsonDecode(response.body);
        return {
          'success': false,
          'error': errorData['error'] ?? 'Failed to get upload URL',
        };
      }
    } catch (e) {
      print('❌ Error getting upload URL: $e');
      return {
        'success': false,
        'error': 'Network error: ${e.toString()}',
      };
    }
  }

  /// Upload item photo file to GCP using signed URL
  Future<Map<String, dynamic>> uploadItemPhoto({
    required String uploadUrl,
    required File photoFile,
    required String contentType,
  }) async {
    try {
      print('📸 Uploading item photo to GCP...');
      print('📸 Upload URL: $uploadUrl');
      print('📸 File path: ${photoFile.path}');
      print('📸 Content type: $contentType');

      final bytes = await photoFile.readAsBytes();
      print('📸 File size: ${bytes.length} bytes');

      final response = await http.put(
        Uri.parse(uploadUrl),
        headers: {
          'Content-Type': contentType,
        },
        body: bytes,
      );

      print('📸 Upload response: ${response.statusCode}');

      if (response.statusCode == 200 || response.statusCode == 204) {
        print('✅ Item photo uploaded successfully');
        return {
          'success': true,
          'message': 'Photo uploaded successfully',
        };
      } else {
        print('❌ Upload failed with status: ${response.statusCode}');
        print('❌ Response body: ${response.body}');
        return {
          'success': false,
          'error': 'Failed to upload photo: ${response.statusCode}',
        };
      }
    } catch (e) {
      print('❌ Error uploading photo: $e');
      return {
        'success': false,
        'error': 'Network error: ${e.toString()}',
      };
    }
  }

  /// Complete item photo upload workflow for a delivery
  ///
  /// This method handles the complete workflow for uploading an item photo:
  /// 1. Gets a signed upload URL from the backend
  /// 2. Uploads the photo file to GCP using the signed URL
  /// 3. Returns the photo URL and delivery information
  ///
  /// Usage example:
  /// ```dart
  /// final result = await deliveryService.uploadDeliveryItemPhoto(
  ///   deliveryId: 123,
  ///   photoFile: File('/path/to/photo.jpg'),
  /// );
  ///
  /// if (result['success']) {
  ///   print('Photo uploaded: ${result['item_photo_url']}');
  /// }
  /// ```
  Future<Map<String, dynamic>> uploadDeliveryItemPhoto({
    required int deliveryId,
    required File photoFile,
    String? filename,
  }) async {
    try {
      // Generate filename if not provided
      final photoFilename = filename ??
          'item_photo_${deliveryId}_${DateTime.now().millisecondsSinceEpoch}.jpg';

      // Determine content type based on file extension
      String contentType = 'image/jpeg'; // Default
      final extension = photoFilename.toLowerCase().split('.').last;
      switch (extension) {
        case 'png':
          contentType = 'image/png';
          break;
        case 'gif':
          contentType = 'image/gif';
          break;
        case 'webp':
          contentType = 'image/webp';
          break;
        case 'jpg':
        case 'jpeg':
          contentType = 'image/jpeg';
          break;
        default:
          contentType = 'image/jpeg';
      }

      print('📸 Starting item photo upload workflow for delivery: $deliveryId');
      print('📸 Filename: $photoFilename');
      print('📸 Content type: $contentType');

      // Step 1: Get signed upload URL
      final uploadUrlResult = await getItemPhotoUploadUrl(
        deliveryId: deliveryId,
        filename: photoFilename,
        contentType: contentType,
      );

      if (!uploadUrlResult['success']) {
        return uploadUrlResult;
      }

      final uploadUrl = uploadUrlResult['upload_url'];
      final itemPhotoUrl = uploadUrlResult['item_photo_url'];

      print('📸 Got upload URL: $uploadUrl');
      print('📸 Item photo URL: $itemPhotoUrl');

      // Step 2: Upload file to GCP
      final uploadResult = await uploadItemPhoto(
        uploadUrl: uploadUrl,
        photoFile: photoFile,
        contentType: contentType,
      );

      if (!uploadResult['success']) {
        return uploadResult;
      }

      // Step 3: Update delivery with photo URL
      print('📸 Updating delivery with photo URL...');
      final updateUrl = Uri.parse('$apiBaseUrl/deliveries/$deliveryId/item-photo');
      
      final updateResponse = await http.put(
        updateUrl,
        headers: await _getHeaders(),
        body: jsonEncode({
          'item_photo_url': itemPhotoUrl,
          'object_key': uploadUrlResult['object_key'],
        }),
      );

      print('📸 Update response: ${updateResponse.statusCode} - ${updateResponse.body}');

      if (updateResponse.statusCode == 200) {
        print('✅ Delivery updated with photo URL successfully');
      } else {
        print('⚠️ Failed to update delivery with photo URL: ${updateResponse.body}');
        // Don't fail the upload if update fails - photo is already uploaded
      }

      // Step 4: Return success with photo URL
      print('✅ Item photo upload workflow completed successfully');
      return {
        'success': true,
        'data': {
          'item_photo_url': itemPhotoUrl,
          'delivery_id': deliveryId,
          'message': 'Item photo uploaded and delivery updated successfully',
        },
        'item_photo_url': itemPhotoUrl,
        'delivery_id': deliveryId,
      };
    } catch (e) {
      print('❌ Error in item photo upload workflow: $e');
      return {
        'success': false,
        'error': 'Failed to upload item photo: ${e.toString()}',
      };
    }
  }
}
