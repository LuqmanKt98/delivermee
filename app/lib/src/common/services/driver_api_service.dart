import 'dart:convert';
import 'dart:io';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../../models/driver_model.dart';
import '../../models/delivery_model.dart';
import '../constant/api_config.dart';

class DriverApiService {
  static String get baseUrl => ApiConfig.driversEndpoint;

  static Future<Map<String, String>> _getHeaders() async {
    final token = await FirebaseAuth.instance.currentUser?.getIdToken();
    return {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  // ── Registration ──────────────────────────────────────────────────────────

  /// Create driver profile in Firestore after Firebase sign-up.
  /// Email comes from the Firebase ID token on the backend — do NOT pass it here.
  static Future<DriverRegistrationResponse> register({
    required String phoneNumber,
    required String firstName,
    required String lastName,
    required String driverLicenseNumber,
    required String vehicleType,
    required String vehicleMake,
    required String vehicleModel,
    required int vehicleYear,
    required String vehiclePlateNumber,
    String? drivingLicenseImage,
    String? idCardImage,
    bool isAvailable = true,
  }) async {
    try {
      final requestBody = {
        'phone_number': phoneNumber,
        'first_name': firstName,
        'last_name': lastName,
        'license_number': driverLicenseNumber,
        'vehicle_type': vehicleType,
        'vehicle_make': vehicleMake,
        'vehicle_model': vehicleModel,
        'vehicle_year': vehicleYear,
        'vehicle_plate_number': vehiclePlateNumber,
        if (drivingLicenseImage != null)
          'driving_license_image': drivingLicenseImage,
        if (idCardImage != null) 'id_card_image': idCardImage,
        'is_available': isAvailable,
      };

      final response = await http.post(
        Uri.parse('$baseUrl/register'),
        headers: await _getHeaders(),
        body: jsonEncode(requestBody),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body);
        final driver = DriverModel.fromJson(data['driver'] ?? {});
        await _cacheDriver(driver);
        return DriverRegistrationResponse(
          message: data['message'] ?? '',
          driver: driver,
          accessToken: '',
        );
      }
      final data = jsonDecode(response.body);
      throw DriverApiError.fromJson(data);
    } catch (e) {
      if (e is DriverApiError) rethrow;
      throw DriverApiError(error: 'Network error: ${e.toString()}');
    }
  }

  // ── Auth helpers ──────────────────────────────────────────────────────────

  static Future<void> logout() async {
    await FirebaseAuth.instance.signOut();
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('driver_data');
    await prefs.remove('driver_id');
    await prefs.remove('driver_email');
    await prefs.remove('driver_first_name');
    await prefs.remove('driver_last_name');
    await prefs.remove('driver_phone_number');
  }

  static bool isLoggedIn() => FirebaseAuth.instance.currentUser != null;

  static Future<DriverModel?> getCurrentDriver() async {
    final prefs = await SharedPreferences.getInstance();
    final driverData = prefs.getString('driver_data');
    if (driverData != null) {
      return DriverModel.fromJson(jsonDecode(driverData));
    }
    return null;
  }

  static Future<void> _cacheDriver(DriverModel driver) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('driver_data', jsonEncode(driver.toJson()));
    if (driver.id != null) await prefs.setInt('driver_id', driver.id!);
    await prefs.setString('driver_email', driver.email);
    await prefs.setString('driver_first_name', driver.firstName);
    await prefs.setString('driver_last_name', driver.lastName);
    await prefs.setString('driver_phone_number', driver.phoneNumber);
  }

  // ── Profile ───────────────────────────────────────────────────────────────

  static Future<DriverModel> getProfile() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/profile'),
        headers: await _getHeaders(),
      );

      final data = jsonDecode(response.body);
      if (response.statusCode == 200) {
        final driver = DriverModel.fromJson(data);
        await _cacheDriver(driver);
        return driver;
      }
      throw DriverApiError.fromJson(data);
    } catch (e) {
      if (e is DriverApiError) rethrow;
      throw DriverApiError(error: 'Network error: ${e.toString()}');
    }
  }

  static Future<Map<String, dynamic>> updateProfile({
    required String firstName,
    required String lastName,
    required String phoneNumber,
    String? password,
  }) async {
    try {
      final body = {
        'first_name': firstName,
        'last_name': lastName,
        'phone_number': phoneNumber,
        if (password != null && password.isNotEmpty) 'password': password,
      };

      final response = await http.put(
        Uri.parse('$baseUrl/profile'),
        headers: await _getHeaders(),
        body: jsonEncode(body),
      );

      final data = jsonDecode(response.body);
      if (response.statusCode == 200) {
        final prefs = await SharedPreferences.getInstance();
        if (data['driver'] != null) {
          await prefs.setString('driver_data', jsonEncode(data['driver']));
        }
        return data;
      }
      throw DriverApiError.fromJson(data);
    } catch (e) {
      if (e is DriverApiError) rethrow;
      throw DriverApiError(error: 'Network error: ${e.toString()}');
    }
  }

  // ── Location ──────────────────────────────────────────────────────────────

  static Future<Map<String, dynamic>> updateLocation({
    required double latitude,
    required double longitude,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/location'),
        headers: await _getHeaders(),
        body: jsonEncode({'latitude': latitude, 'longitude': longitude}),
      );
      final data = jsonDecode(response.body);
      if (response.statusCode == 200) return data;
      throw DriverApiError.fromJson(data);
    } catch (e) {
      if (e is DriverApiError) rethrow;
      throw DriverApiError(error: 'Network error: ${e.toString()}');
    }
  }

  // ── Push token ────────────────────────────────────────────────────────────

  static Future<Map<String, dynamic>> updatePushToken({
    required String pushToken,
    String? deviceId,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/push-token'),
        headers: await _getHeaders(),
        body: jsonEncode({
          'push_token': pushToken,
          if (deviceId != null) 'device_id': deviceId,
        }),
      );
      final data = jsonDecode(response.body);
      if (response.statusCode == 200) return data;
      throw DriverApiError.fromJson(data);
    } catch (e) {
      if (e is DriverApiError) rethrow;
      throw DriverApiError(error: 'Network error: ${e.toString()}');
    }
  }

  // ── Status / Availability ─────────────────────────────────────────────────

  static Future<Map<String, dynamic>> updateStatus({
    required String status,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/status'),
        headers: await _getHeaders(),
        body: jsonEncode({'status': status}),
      );
      final data = jsonDecode(response.body);
      if (response.statusCode == 200) return data;
      throw DriverApiError.fromJson(data);
    } catch (e) {
      if (e is DriverApiError) rethrow;
      throw DriverApiError(error: 'Network error: ${e.toString()}');
    }
  }

  static Future<Map<String, dynamic>> updateAvailability({
    required bool isAvailable,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/availability'),
        headers: await _getHeaders(),
        body: jsonEncode({'is_available': isAvailable}),
      );
      final data = jsonDecode(response.body);
      if (response.statusCode == 200) return data;
      throw DriverApiError.fromJson(data);
    } catch (e) {
      if (e is DriverApiError) rethrow;
      throw DriverApiError(error: 'Network error: ${e.toString()}');
    }
  }

  // ── Payment method ────────────────────────────────────────────────────────

  static Future<Map<String, dynamic>> updatePaymentMethod({
    required bool hasPaymentMethod,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/payment-method'),
        headers: await _getHeaders(),
        body: jsonEncode({'has_payment_method': hasPaymentMethod}),
      );
      final data = jsonDecode(response.body);
      if (response.statusCode == 200) return data;
      throw DriverApiError.fromJson(data);
    } catch (e) {
      if (e is DriverApiError) rethrow;
      throw DriverApiError(error: 'Network error: ${e.toString()}');
    }
  }

  // ── Documents ─────────────────────────────────────────────────────────────

  static Future<Map<String, dynamic>> updateDocuments({
    required String? drivingLicenseImage,
    required String? idCardImage,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/documents'),
        headers: await _getHeaders(),
        body: jsonEncode({
          if (drivingLicenseImage != null)
            'driving_license_image': drivingLicenseImage,
          if (idCardImage != null) 'id_card_image': idCardImage,
        }),
      );
      final data = jsonDecode(response.body);
      if (response.statusCode == 200) return data;
      throw DriverApiError.fromJson(data);
    } catch (e) {
      if (e is DriverApiError) rethrow;
      throw DriverApiError(error: 'Network error: ${e.toString()}');
    }
  }

  // ── Notifications ─────────────────────────────────────────────────────────

  static Future<Map<String, dynamic>> getNotifications({
    String? status,
    int limit = 20,
    int offset = 0,
  }) async {
    try {
      final queryParams = <String, String>{
        'limit': limit.toString(),
        'offset': offset.toString(),
        if (status != null) 'status': status,
      };
      final uri = Uri.parse('$baseUrl/notifications')
          .replace(queryParameters: queryParams);
      final response = await http.get(uri, headers: await _getHeaders());
      final data = jsonDecode(response.body);
      if (response.statusCode == 200) return data;
      throw DriverApiError.fromJson(data);
    } catch (e) {
      if (e is DriverApiError) rethrow;
      throw DriverApiError(error: 'Network error: ${e.toString()}');
    }
  }

  static Future<Map<String, dynamic>> markNotificationAsRead({
    required int notificationId,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/notifications/$notificationId/read'),
        headers: await _getHeaders(),
      );
      final data = jsonDecode(response.body);
      if (response.statusCode == 200) return data;
      throw DriverApiError.fromJson(data);
    } catch (e) {
      if (e is DriverApiError) rethrow;
      throw DriverApiError(error: 'Network error: ${e.toString()}');
    }
  }

  // ── Rides ─────────────────────────────────────────────────────────────────

  static Future<Map<String, dynamic>> acceptRide({required int rideId}) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/rides/$rideId/accept'),
        headers: await _getHeaders(),
      );
      final data = jsonDecode(response.body);
      if (response.statusCode == 200) return data;
      throw DriverApiError.fromJson(data);
    } catch (e) {
      if (e is DriverApiError) rethrow;
      throw DriverApiError(error: 'Network error: ${e.toString()}');
    }
  }

  static Future<Map<String, dynamic>> rejectRide({required int rideId}) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/rides/$rideId/reject'),
        headers: await _getHeaders(),
      );
      final data = jsonDecode(response.body);
      if (response.statusCode == 200) return data;
      throw DriverApiError.fromJson(data);
    } catch (e) {
      if (e is DriverApiError) rethrow;
      throw DriverApiError(error: 'Network error: ${e.toString()}');
    }
  }

  // ── Document upload ───────────────────────────────────────────────────────

  static Future<DocumentUploadResponse> getDocumentUploadUrl({
    required String docType,
    required String filename,
    required String contentType,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/documents/upload-url'),
        headers: await _getHeaders(),
        body: jsonEncode({
          'doc_type': docType,
          'filename': filename,
          'content_type': contentType,
        }),
      );
      final data = jsonDecode(response.body);
      if (response.statusCode == 200) return DocumentUploadResponse.fromJson(data);
      throw DriverApiError.fromJson(data);
    } catch (e) {
      if (e is DriverApiError) rethrow;
      throw DriverApiError(error: 'Network error: ${e.toString()}');
    }
  }

  static Future<Map<String, dynamic>> confirmDocumentUpload({
    required String docType,
    required String objectKey,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/documents/confirm-upload'),
        headers: await _getHeaders(),
        body: jsonEncode({'doc_type': docType, 'object_key': objectKey}),
      );
      final data = jsonDecode(response.body);
      if (response.statusCode == 200) return data;
      throw DriverApiError.fromJson(data);
    } catch (e) {
      if (e is DriverApiError) rethrow;
      throw DriverApiError(error: 'Network error: ${e.toString()}');
    }
  }

  static Future<List<DocumentUploadResponse>> getRegistrationUploadUrls({
    required List<DocumentUploadRequest> documents,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/register/upload-urls'),
        headers: await _getHeaders(),
        body: jsonEncode(
            {'documents': documents.map((doc) => doc.toJson()).toList()}),
      );
      final data = jsonDecode(response.body);
      if (response.statusCode == 200) {
        final List<dynamic> uploadUrls = data['upload_urls'];
        return uploadUrls
            .map((url) => DocumentUploadResponse.fromJson(url))
            .toList();
      }
      throw DriverApiError.fromJson(data);
    } catch (e) {
      if (e is DriverApiError) rethrow;
      throw DriverApiError(error: 'Network error: ${e.toString()}');
    }
  }

  static Future<DocumentUploadResponse> getPublicDocumentUploadUrl({
    required int driverId,
    required String docType,
    required String filename,
    required String contentType,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/documents/upload-url/public'),
        headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
        body: jsonEncode({
          'driver_id': driverId,
          'doc_type': docType,
          'filename': filename,
          'content_type': contentType,
        }),
      );
      final data = jsonDecode(response.body);
      if (response.statusCode == 200) return DocumentUploadResponse.fromJson(data);
      throw DriverApiError.fromJson(data);
    } catch (e) {
      if (e is DriverApiError) rethrow;
      throw DriverApiError(error: 'Network error: ${e.toString()}');
    }
  }

  // ── Deliveries ────────────────────────────────────────────────────────────

  static Future<AssignedDeliveriesResponse> getAssignedDeliveries({
    int limit = 50,
    int offset = 0,
  }) async {
    try {
      final uri = Uri.parse('${ApiConfig.deliveriesEndpoint}/driver/assigned')
          .replace(queryParameters: {
        'limit': limit.toString(),
        'offset': offset.toString(),
      });
      final response = await http.get(uri, headers: await _getHeaders());
      if (response.statusCode == 200) {
        return AssignedDeliveriesResponse.fromJson(jsonDecode(response.body));
      }
      String errorMsg = 'Failed to load deliveries';
      if (response.statusCode == 401) errorMsg = 'Authentication failed. Please login again.';
      throw DriverApiError(error: errorMsg, details: 'Status: ${response.statusCode}');
    } catch (e) {
      if (e is DriverApiError) rethrow;
      throw DriverApiError(error: 'Network error: ${e.toString()}');
    }
  }

  static Future<Map<String, dynamic>> getDriverDeliveryHistory({
    int limit = 50,
    int offset = 0,
  }) async {
    try {
      final uri = Uri.parse('${ApiConfig.deliveriesEndpoint}/driver/history')
          .replace(queryParameters: {
        'limit': limit.toString(),
        'offset': offset.toString(),
      });
      final response = await http.get(uri, headers: await _getHeaders());
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body);
        List<dynamic> deliveriesJson = decoded is Map ? (decoded['deliveries'] ?? []) : decoded;
        final deliveries = deliveriesJson
            .map((d) => DeliveryModel.fromJson(d as Map<String, dynamic>))
            .toList();
        return {
          'success': true,
          'deliveries': deliveries,
          'total': decoded is Map ? (decoded['total'] ?? deliveries.length) : deliveries.length,
          'limit': limit,
          'offset': offset,
        };
      }
      String errorMsg = 'Failed to load delivery history';
      if (response.statusCode == 401) errorMsg = 'Authentication failed. Please login again.';
      throw DriverApiError(error: errorMsg, details: 'Status: ${response.statusCode}');
    } catch (e) {
      if (e is DriverApiError) rethrow;
      throw DriverApiError(error: 'Network error: ${e.toString()}');
    }
  }

  static Future<Map<String, dynamic>> getDriverAcceptedDeliveries({
    int limit = 50,
    int offset = 0,
    int days = 7,
  }) async {
    try {
      final uri = Uri.parse('${ApiConfig.deliveriesEndpoint}/driver/accepted')
          .replace(queryParameters: {
        'limit': limit.toString(),
        'offset': offset.toString(),
        'days': days.toString(),
      });
      final response = await http.get(uri, headers: await _getHeaders());
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body);
        List<dynamic> deliveriesJson = decoded is Map ? (decoded['deliveries'] ?? []) : decoded;
        final deliveries = deliveriesJson
            .map((d) => DeliveryModel.fromJson(d as Map<String, dynamic>))
            .toList();
        return {
          'success': true,
          'deliveries': deliveries,
          'total': decoded is Map ? (decoded['total'] ?? deliveries.length) : deliveries.length,
          'limit': limit,
          'offset': offset,
        };
      }
      String errorMsg = 'Failed to load accepted deliveries';
      if (response.statusCode == 401) errorMsg = 'Authentication failed. Please login again.';
      throw DriverApiError(error: errorMsg, details: 'Status: ${response.statusCode}');
    } catch (e) {
      if (e is DriverApiError) rethrow;
      throw DriverApiError(error: 'Network error: ${e.toString()}');
    }
  }

  static Future<Map<String, dynamic>> acceptDelivery(int deliveryId) async {
    try {
      final response = await http.post(
        Uri.parse('${ApiConfig.deliveriesEndpoint}/$deliveryId/accept'),
        headers: await _getHeaders(),
      );
      final data = jsonDecode(response.body);
      if (response.statusCode == 200) return data;
      throw DriverApiError.fromJson(data);
    } catch (e) {
      if (e is DriverApiError) rethrow;
      throw DriverApiError(error: 'Network error: ${e.toString()}');
    }
  }

  static Future<Map<String, dynamic>> rejectDelivery(int deliveryId) async {
    try {
      final response = await http.post(
        Uri.parse('${ApiConfig.deliveriesEndpoint}/$deliveryId/reject'),
        headers: await _getHeaders(),
      );
      final data = jsonDecode(response.body);
      if (response.statusCode == 200) return data;
      throw DriverApiError.fromJson(data);
    } catch (e) {
      if (e is DriverApiError) rethrow;
      throw DriverApiError(error: 'Network error: ${e.toString()}');
    }
  }

  static Future<Map<String, dynamic>> pickupDelivery(int deliveryId) async {
    try {
      final response = await http.post(
        Uri.parse('${ApiConfig.deliveriesEndpoint}/$deliveryId/pickup'),
        headers: await _getHeaders(),
      );
      final data = jsonDecode(response.body);
      if (response.statusCode == 200) return data;
      throw DriverApiError.fromJson(data);
    } catch (e) {
      if (e is DriverApiError) rethrow;
      throw DriverApiError(error: 'Network error: ${e.toString()}');
    }
  }

  static Future<Map<String, dynamic>> startTransitDelivery(
      int deliveryId) async {
    try {
      final response = await http.post(
        Uri.parse('${ApiConfig.deliveriesEndpoint}/$deliveryId/start-transit'),
        headers: await _getHeaders(),
      );
      final data = jsonDecode(response.body);
      if (response.statusCode == 200) return data;
      throw DriverApiError.fromJson(data);
    } catch (e) {
      if (e is DriverApiError) rethrow;
      throw DriverApiError(error: 'Network error: ${e.toString()}');
    }
  }

  static Future<Map<String, dynamic>> completeDelivery(int deliveryId) async {
    try {
      final response = await http.post(
        Uri.parse('${ApiConfig.deliveriesEndpoint}/$deliveryId/complete'),
        headers: await _getHeaders(),
      );
      final data = jsonDecode(response.body);
      if (response.statusCode == 200) return data;
      throw DriverApiError.fromJson(data);
    } catch (e) {
      if (e is DriverApiError) rethrow;
      throw DriverApiError(error: 'Network error: ${e.toString()}');
    }
  }

  static Future<Map<String, dynamic>> cancelDelivery({
    required int deliveryId,
    String? cancellationReason,
    double? rating,
    String? review,
  }) async {
    try {
      final body = {
        if (cancellationReason != null && cancellationReason.isNotEmpty)
          'cancellation_reason': cancellationReason,
        if (rating != null) 'rating': rating,
        if (review != null && review.isNotEmpty) 'review': review,
      };

      final response = await http.post(
        Uri.parse('${ApiConfig.deliveriesEndpoint}/$deliveryId/cancel'),
        headers: await _getHeaders(),
        body: body.isNotEmpty ? jsonEncode(body) : null,
      );
      final data = jsonDecode(response.body);
      if (response.statusCode == 200) return data;
      throw DriverApiError.fromJson(data);
    } catch (e) {
      if (e is DriverApiError) rethrow;
      throw DriverApiError(error: 'Network error: ${e.toString()}');
    }
  }

  // ── Item photo upload ─────────────────────────────────────────────────────

  static Future<Map<String, dynamic>> getDriverItemPhotoUploadUrl({
    required int deliveryId,
    required String filename,
    required String contentType,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/deliveries/$deliveryId/item-photo/upload-url'),
        headers: await _getHeaders(),
        body: jsonEncode({'filename': filename, 'content_type': contentType}),
      );
      final data = jsonDecode(response.body);
      if (response.statusCode == 200) {
        return {
          'success': true,
          'upload_url': data['upload_url'],
          'object_key': data['object_key'],
          'expires_in': data['expires_in'],
        };
      }
      return {'success': false, 'error': data['error'] ?? 'Failed to get upload URL'};
    } catch (e) {
      return {'success': false, 'error': 'Network error: ${e.toString()}'};
    }
  }

  static Future<Map<String, dynamic>> uploadDriverItemPhoto({
    required String uploadUrl,
    required File photoFile,
    required String contentType,
  }) async {
    try {
      final bytes = await photoFile.readAsBytes();
      final response = await http.put(
        Uri.parse(uploadUrl),
        headers: {'Content-Type': contentType},
        body: bytes,
      );
      if (response.statusCode == 200 || response.statusCode == 204) {
        return {'success': true, 'message': 'Photo uploaded successfully'};
      }
      return {'success': false, 'error': 'Failed to upload photo: ${response.statusCode}'};
    } catch (e) {
      return {'success': false, 'error': 'Network error: ${e.toString()}'};
    }
  }

  static Future<Map<String, dynamic>> uploadDriverDeliveryItemPhoto({
    required int deliveryId,
    required File photoFile,
    String? filename,
  }) async {
    try {
      final photoFilename = filename ??
          'driver_item_photo_${deliveryId}_${DateTime.now().millisecondsSinceEpoch}.jpg';
      String contentType = 'image/jpeg';
      final ext = photoFilename.toLowerCase().split('.').last;
      if (ext == 'png') contentType = 'image/png';
      if (ext == 'gif') contentType = 'image/gif';
      if (ext == 'webp') contentType = 'image/webp';

      final uploadUrlResult = await getDriverItemPhotoUploadUrl(
        deliveryId: deliveryId,
        filename: photoFilename,
        contentType: contentType,
      );
      if (!(uploadUrlResult['success'] as bool)) return uploadUrlResult;

      final uploadResult = await uploadDriverItemPhoto(
        uploadUrl: uploadUrlResult['upload_url'],
        photoFile: photoFile,
        contentType: contentType,
      );
      if (!(uploadResult['success'] as bool)) return uploadResult;

      return {
        'success': true,
        'data': {
          'item_photo_url': uploadUrlResult['object_key'],
          'delivery_id': deliveryId,
        },
        'item_photo_url': uploadUrlResult['object_key'],
        'delivery_id': deliveryId,
      };
    } catch (e) {
      return {'success': false, 'error': 'Failed to upload driver item photo: ${e.toString()}'};
    }
  }

  // ── Generic POST ─────────────────────────────────────────────────────────

  static Future<Map<String, dynamic>> post(
    String endpoint,
    Map<String, dynamic> body,
  ) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl$endpoint'),
        headers: await _getHeaders(),
        body: jsonEncode(body),
      );
      final data = jsonDecode(response.body);
      if (response.statusCode == 200 || response.statusCode == 201) {
        return data;
      }
      throw DriverApiError.fromJson(data);
    } catch (e) {
      if (e is DriverApiError) rethrow;
      throw DriverApiError(error: 'Network error: ${e.toString()}');
    }
  }

  // Debug
  static Future<Map<String, dynamic>> testDriverEndpoint() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/test'),
        headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
      );
      return jsonDecode(response.body);
    } catch (e) {
      return {'error': 'Test failed: ${e.toString()}'};
    }
  }
}
