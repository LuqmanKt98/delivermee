import 'dart:convert';
import 'dart:math' as math;
import 'package:http/http.dart' as http;
import 'package:get/get.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:deliver_mee/src/feature/user/home/controller/controller.dart';
import '../constant/api_config.dart';

class PricingService extends GetxController {
  static PricingService get to => Get.find<PricingService>();

  // Using centralized API configuration
  String get apiBaseUrl => ApiConfig.baseUrl;

  // Pricing state
  final RxDouble calculatedFare = 0.0.obs;
  final RxBool isLoadingPricing = false.obs;
  final RxString pricingError = ''.obs;

  // Pricing details
  final RxMap<String, dynamic> fareDetails = <String, dynamic>{}.obs;
  final RxDouble baseFare = 0.0.obs;
  final RxDouble distanceFare = 0.0.obs;
  final RxDouble timeFare = 0.0.obs;
  final RxDouble surgeMultiplier = 1.0.obs;
  final RxDouble totalFare = 0.0.obs;

  /// Calculate fare for delivery
  Future<Map<String, dynamic>> calculateFare({
    required double pickupLatitude,
    required double pickupLongitude,
    required double dropoffLatitude,
    required double dropoffLongitude,
    required String vehicleType,
    String serviceType = 'delivery',
    double? distance,
    double? duration,
    double surgeMultiplier = 1.0,
  }) async {
    try {
      isLoadingPricing.value = true;
      pricingError.value = '';

      final url = Uri.parse('$apiBaseUrl/pricing/calculate-fare');

      final requestBody = {
        'pickup_latitude': pickupLatitude,
        'pickup_longitude': pickupLongitude,
        'dropoff_latitude': dropoffLatitude,
        'dropoff_longitude': dropoffLongitude,
        'vehicle_type': vehicleType,
        'service_type': serviceType,
        'surge_multiplier': surgeMultiplier,
      };

      // Add optional parameters if provided
      if (distance != null) requestBody['distance'] = distance;
      if (duration != null) requestBody['duration'] = duration;

      print('💰 Calculating fare with data: ${jsonEncode(requestBody)}');
      print('🔗 Pricing API URL: $url');

      // Debug headers
      final headers = await _getHeaders();
      print('🔐 Pricing API Headers: $headers');

      // Validate coordinates are within valid ranges
      if (pickupLatitude < -90 ||
          pickupLatitude > 90 ||
          pickupLongitude < -180 ||
          pickupLongitude > 180 ||
          dropoffLatitude < -90 ||
          dropoffLatitude > 90 ||
          dropoffLongitude < -180 ||
          dropoffLongitude > 180) {
        throw Exception('Invalid coordinates provided for fare calculation');
      }

      final response = await http
          .post(
        url,
        headers: await _getHeaders(),
        body: jsonEncode(requestBody),
      )
          .timeout(
        Duration(seconds: 30),
        onTimeout: () {
          throw Exception('Pricing API request timed out');
        },
      );

      print(
          '📡 Pricing API Response: ${response.statusCode} - ${response.body}');

      if (response.statusCode == 200) {
        final responseData = jsonDecode(response.body);
        print('📊 Raw API Response: $responseData');

        // Update pricing state - handle different response formats
        fareDetails.value = responseData;

        // Try different possible field names for total fare
        double apiTotalFare = 0.0;
        if (responseData['total_fare'] != null) {
          apiTotalFare = responseData['total_fare'].toDouble();
        } else if (responseData['total'] != null) {
          apiTotalFare = responseData['total'].toDouble();
        } else if (responseData['amount'] != null) {
          apiTotalFare = responseData['amount'].toDouble();
        } else if (responseData['fare'] != null) {
          apiTotalFare = responseData['fare'].toDouble();
        }

        // If no total found, calculate from components
        if (apiTotalFare == 0.0) {
          final base = responseData['base_fare']?.toDouble() ??
              responseData['base']?.toDouble() ??
              0.0;
          final distance = responseData['distance_fare']?.toDouble() ??
              responseData['distance']?.toDouble() ??
              0.0;
          final time = responseData['time_fare']?.toDouble() ??
              responseData['time']?.toDouble() ??
              0.0;
          apiTotalFare = base + distance + time;
        }

        calculatedFare.value = apiTotalFare;
        baseFare.value = responseData['base_fare']?.toDouble() ??
            responseData['base']?.toDouble() ??
            0.0;
        distanceFare.value = responseData['distance_fare']?.toDouble() ??
            responseData['distance']?.toDouble() ??
            0.0;
        timeFare.value = responseData['time_fare']?.toDouble() ??
            responseData['time']?.toDouble() ??
            0.0;
        this.surgeMultiplier.value =
            responseData['surge_multiplier']?.toDouble() ??
                responseData['surge']?.toDouble() ??
                1.0;
        totalFare.value = apiTotalFare;

        print(
            '✅ Fare calculated successfully: \$${totalFare.value.toStringAsFixed(2)}');
        print(
            '📊 Fare breakdown: Base: \$${baseFare.value.toStringAsFixed(2)}, Distance: \$${distanceFare.value.toStringAsFixed(2)}, Time: \$${timeFare.value.toStringAsFixed(2)}');

        return {
          'success': true,
          'data': responseData,
          'total_fare': totalFare.value,
        };
      } else {
        print(
            '❌ Pricing calculation failed with status: ${response.statusCode}');
        print('❌ Response body: ${response.body}');

        try {
          final errorData = jsonDecode(response.body);
          final errorMessage = errorData['error'] ??
              errorData['message'] ??
              'Failed to calculate fare';

          // Handle specific error cases
          String userFriendlyError = errorMessage;
          if (response.statusCode == 401) {
            userFriendlyError = 'Authentication failed. Please login again.';
          } else if (response.statusCode == 400) {
            // Check if it's a backend server error vs validation error
            if (errorMessage.contains('flask_restx') ||
                errorMessage.contains('module') ||
                errorMessage.contains('attribute')) {
              userFriendlyError =
                  'Pricing service temporarily unavailable. Using default pricing.';
            } else {
              userFriendlyError =
                  'Invalid request data. Please check your locations.';
            }
          } else if (response.statusCode == 500) {
            userFriendlyError = 'Server error. Please try again later.';
          }

          pricingError.value = userFriendlyError;
          return {
            'success': false,
            'error': userFriendlyError,
          };
        } catch (e) {
          pricingError.value = 'Server error: ${response.statusCode}';
          return {
            'success': false,
            'error': 'Server error: ${response.statusCode} - ${response.body}',
          };
        }
      }
    } catch (e) {
      print('❌ Pricing calculation error: $e');
      pricingError.value = 'Network error: ${e.toString()}';
      return {
        'success': false,
        'error': 'Network error: ${e.toString()}',
      };
    } finally {
      isLoadingPricing.value = false;
    }
  }

  /// Set pricing from delivery response estimated cost
  void setPricingFromDeliveryResponse(double estimatedCost) {
    print(
        '💰 Setting pricing from delivery response: \$${estimatedCost.toStringAsFixed(2)}');
    totalFare.value = estimatedCost;
    calculatedFare.value = estimatedCost;

    // Clear any previous errors since we have valid pricing
    pricingError.value = '';

    // Set reasonable breakdown for display purposes
    baseFare.value = estimatedCost * 0.6; // 60% base fare
    distanceFare.value = estimatedCost * 0.4; // 40% distance fare
    timeFare.value = 0.0;
    surgeMultiplier.value = 1.0;

    print(
        '✅ Pricing set from delivery response: \$${totalFare.value.toStringAsFixed(2)}');
  }

  /// Set pricing from complete delivery response data
  void setPricingFromDeliveryData(Map<String, dynamic> deliveryData) {
    print('💰 Setting pricing from complete delivery data: $deliveryData');

    // Extract estimated cost from delivery response - robust extraction
    double estimatedCost = 0.0;

    // Try different possible field names for cost in nested structure
    if (deliveryData['delivery'] != null) {
      final delivery = deliveryData['delivery'];
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
      if (deliveryData['estimated_cost'] != null) {
        estimatedCost = deliveryData['estimated_cost'].toDouble();
        print('💰 Found cost in estimated_cost: $estimatedCost');
      } else if (deliveryData['cost'] != null) {
        estimatedCost = deliveryData['cost'].toDouble();
        print('💰 Found cost in cost: $estimatedCost');
      } else if (deliveryData['total_cost'] != null) {
        estimatedCost = deliveryData['total_cost'].toDouble();
        print('💰 Found cost in total_cost: $estimatedCost');
      } else if (deliveryData['price'] != null) {
        estimatedCost = deliveryData['price'].toDouble();
        print('💰 Found cost in price: $estimatedCost');
      }
    }

    // If still no cost found, try to extract from any numeric field that might be the cost
    if (estimatedCost == 0.0) {
      print(
          '⚠️ No cost found in expected fields, searching for any numeric value...');
      for (String key in deliveryData.keys) {
        if (deliveryData[key] is num && deliveryData[key] > 0) {
          print('🔍 Found numeric value in $key: ${deliveryData[key]}');
          // If it's a reasonable delivery cost (between $5 and $500)
          if (deliveryData[key] >= 5.0 && deliveryData[key] <= 500.0) {
            estimatedCost = deliveryData[key].toDouble();
            print('💰 Using $key as cost: $estimatedCost');
            break;
          }
        }
      }
    }

    if (estimatedCost > 0) {
      setPricingFromDeliveryResponse(estimatedCost);
    } else {
      print(
          '⚠️ No estimated cost found in delivery data, using default pricing');
      setDefaultPricing();
    }
  }

  /// Set default pricing values when API is unavailable
  void setDefaultPricing() {
    print('⚠️ Setting default pricing due to API unavailability');

    // Check if we have delivery price from HomeController first
    try {
      final homeController = Get.find<HomeController>();
      if (homeController.deliveryPrice.value > 0) {
        print(
            '💰 Using delivery price from HomeController: \$${homeController.deliveryPrice.value.toStringAsFixed(2)}');
        totalFare.value = homeController.deliveryPrice.value;
        calculatedFare.value = homeController.deliveryPrice.value;

        // Set reasonable breakdown for display
        baseFare.value = homeController.deliveryPrice.value * 0.6;
        distanceFare.value = homeController.deliveryPrice.value * 0.4;
        timeFare.value = 0.0;
        surgeMultiplier.value = 1.0;

        // Clear error since we have valid pricing
        pricingError.value = '';

        print(
            '✅ Using delivery price: \$${totalFare.value.toStringAsFixed(2)}');
        return;
      }
    } catch (e) {
      print('⚠️ Could not access HomeController: $e');
    }

    // Fallback to default pricing if no delivery price available
    baseFare.value = 10.0;
    distanceFare.value = 5.0;
    timeFare.value = 0.0;
    surgeMultiplier.value = 1.0;
    totalFare.value = baseFare.value + distanceFare.value + timeFare.value;
    calculatedFare.value = totalFare.value;

    // Set pricing error to indicate API unavailability
    pricingError.value = 'Estimated Fare API unavailable';

    print('💰 Default pricing set: \$${totalFare.value.toStringAsFixed(2)}');
  }

  /// Manually set the total fare (for cases where we know the exact cost)
  void setTotalFare(double cost) {
    print('💰 Manually setting total fare to: \$${cost.toStringAsFixed(2)}');
    totalFare.value = cost;
    calculatedFare.value = cost;

    // Set reasonable breakdown for display
    baseFare.value = cost * 0.6; // 60% base fare
    distanceFare.value = cost * 0.4; // 40% distance fare
    timeFare.value = 0.0;
    surgeMultiplier.value = 1.0;

    // Clear any errors since we have valid pricing
    pricingError.value = '';

    print('✅ Total fare set to: \$${totalFare.value.toStringAsFixed(2)}');
  }

  /// Get headers for API requests
  Future<Map<String, String>> _getHeaders() async {
    final token = await FirebaseAuth.instance.currentUser?.getIdToken() ?? '';

    print(
        '🔐 Pricing Service - Token retrieved: ${token.isNotEmpty ? "Present" : "Missing"}');
    if (token.isNotEmpty) {
      print('🔐 Pricing Service - Token preview: ${token.substring(0, 20)}...');
    }

    return {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      if (token.isNotEmpty) 'Authorization': 'Bearer $token',
    };
  }

  /// Calculate distance between two coordinates (Haversine formula)
  double calculateDistance(double lat1, double lon1, double lat2, double lon2) {
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

    return distance;
  }

  /// Convert degrees to radians
  double _degreesToRadians(double degrees) {
    return degrees * (math.pi / 180);
  }

  /// Test API connection
  Future<bool> testApiConnection() async {
    try {
      final url = Uri.parse('$apiBaseUrl/pricing/calculate-fare');
      final response = await http
          .post(
            url,
            headers: await _getHeaders(),
            body: jsonEncode({
              'pickup_latitude': 40.7128,
              'pickup_longitude': -74.0060,
              'dropoff_latitude': 40.7589,
              'dropoff_longitude': -73.9851,
              'vehicle_type': 'cargo_van',
              'service_type': 'delivery',
              'distance': 5.0,
            }),
          )
          .timeout(Duration(seconds: 10));

      print('🔗 API Connection Test: ${response.statusCode}');
      return response.statusCode == 200 ||
          response.statusCode == 400; // 400 is OK for test data
    } catch (e) {
      print('❌ API Connection Test Failed: $e');
      return false;
    }
  }

  /// Reset pricing state
  void resetPricing() {
    calculatedFare.value = 0.0;
    isLoadingPricing.value = false;
    pricingError.value = '';
    fareDetails.clear();
    baseFare.value = 0.0;
    distanceFare.value = 0.0;
    timeFare.value = 0.0;
    surgeMultiplier.value = 1.0;
    totalFare.value = 0.0;
  }
}
