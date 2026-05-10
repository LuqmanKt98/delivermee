import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:image_picker/image_picker.dart';
import 'package:intl/intl.dart';
import '../../../../common/services/driver_api_service.dart';
import '../../../../common/services/customer_delivery_tracking_service.dart';

class DriverPickUpController extends GetxController {
  static DriverPickUpController get to => Get.find();

  RxInt ratingIndex = 3.obs;
  void updateRatingIndex(int index) {
    ratingIndex.value = index;
  }

  RxString date = ''.obs;

  TextEditingController timeController = TextEditingController();
  Future<void> pickDateTime(BuildContext context) async {
    // Pick Date
    DateTime? selectedDate = await showDatePicker(
      context: context,
      initialDate: DateTime.now(),
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
    );

    if (selectedDate != null) {
      TimeOfDay? selectedTime = await showTimePicker(
        context: context,
        initialTime: TimeOfDay.now(),
      );

      if (selectedTime != null) {
        String formattedDate =
            DateFormat('dd  MMMM, yyyy').format(selectedDate);
        date.value = formattedDate;

        String formattedTime = selectedTime.format(context);
        timeController.text = formattedTime;
      }

      date.value = '${date.value} ${timeController.text} ';
    }
  }

  File? selectedImage;

  Future<void> pickImage() async {
    final pickedFile =
        await ImagePicker().pickImage(source: ImageSource.camera);

    if (pickedFile != null) {
      selectedImage = File(pickedFile.path);
    }
    update(['selecteImage']);
  }

  File? pickedFilePath;

  Future<void> pickFile() async {
    FilePickerResult? result = await FilePicker.platform.pickFiles();

    if (result != null && result.files.single.path != null) {
      pickedFilePath = File(result.files.single.path!);
      ;
    }
    update(['pickfile']);
  }

  /// Upload delivery item photo using the driver API service
  Future<void> uploadDeliveryItemPhoto(int deliveryId) async {
    if (selectedImage == null) {
      Get.snackbar(
        'Error',
        'Please select an image first',
        backgroundColor: Colors.red,
        colorText: Colors.white,
      );
      return;
    }

    try {
      isLoading.value = true;
      print('📸 Uploading delivery item photo for delivery: $deliveryId');

      final result = await DriverApiService.uploadDriverDeliveryItemPhoto(
        deliveryId: deliveryId,
        photoFile: selectedImage!,
      );

      if (result['success']) {
        print('✅ Delivery item photo uploaded successfully');
        Get.snackbar(
          'Success',
          'Item photo uploaded successfully!',
          backgroundColor: Colors.green,
          colorText: Colors.white,
        );
      } else {
        print('❌ Failed to upload item photo: ${result['error']}');
        Get.snackbar(
          'Error',
          'Failed to upload item photo: ${result['error']}',
          backgroundColor: Colors.red,
          colorText: Colors.white,
        );
      }
    } catch (e) {
      print('❌ Error uploading item photo: $e');
      Get.snackbar(
        'Error',
        'Failed to upload item photo: ${e.toString()}',
        backgroundColor: Colors.red,
        colorText: Colors.white,
      );
    } finally {
      isLoading.value = false;
    }
  }

  // API call methods for delivery actions
  RxBool isLoading = false.obs;

  Future<void> pickupDelivery(int deliveryId) async {
    try {
      isLoading.value = true;
      print('🚚 Picking up delivery: $deliveryId');

      final response = await DriverApiService.pickupDelivery(deliveryId);

      print('✅ Pickup successful: $response');
      print('✅ Backend response data: ${response.toString()}');
      
      // Wait a moment for backend to process the update
      await Future.delayed(Duration(milliseconds: 500));
      
      // Refresh the customer tracking status
      try {
        if (Get.isRegistered<CustomerDeliveryTrackingService>()) {
          print('🔄 Refreshing customer tracking status for delivery: $deliveryId');
          await CustomerDeliveryTrackingService.to.refreshStatus(deliveryId);
          print('🔄 Customer tracking status refreshed after pickup');
        } else {
          print('⚠️ CustomerDeliveryTrackingService not registered');
        }
      } catch (refreshError) {
        print('⚠️ Failed to refresh tracking status: $refreshError');
        // Don't fail the whole operation if refresh fails
      }
      
      Get.snackbar(
        'Success',
        'Delivery picked up successfully!',
        backgroundColor: Colors.green,
        colorText: Colors.white,
      );
    } catch (e) {
      print('❌ Pickup failed: $e');
      Get.snackbar(
        'Error',
        'Failed to pickup delivery: ${e.toString()}',
        backgroundColor: Colors.red,
        colorText: Colors.white,
      );
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> startTransitDelivery(int deliveryId) async {
    try {
      isLoading.value = true;
      print('🚚 Starting transit for delivery: $deliveryId');

      final response = await DriverApiService.startTransitDelivery(deliveryId);

      print('✅ Transit started: $response');
      print('✅ Backend response data: ${response.toString()}');
      
      // Wait a moment for backend to process the update
      await Future.delayed(Duration(milliseconds: 500));
      
      // Refresh the customer tracking status
      try {
        if (Get.isRegistered<CustomerDeliveryTrackingService>()) {
          print('🔄 Refreshing customer tracking status for delivery: $deliveryId');
          await CustomerDeliveryTrackingService.to.refreshStatus(deliveryId);
          print('🔄 Customer tracking status refreshed after starting transit');
        } else {
          print('⚠️ CustomerDeliveryTrackingService not registered');
        }
      } catch (refreshError) {
        print('⚠️ Failed to refresh tracking status: $refreshError');
        // Don't fail the whole operation if refresh fails
      }
      
      Get.snackbar(
        'Success',
        'Transit started successfully!',
        backgroundColor: Colors.green,
        colorText: Colors.white,
      );
    } catch (e) {
      print('❌ Start transit failed: $e');
      Get.snackbar(
        'Error',
        'Failed to start transit: ${e.toString()}',
        backgroundColor: Colors.red,
        colorText: Colors.white,
      );
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> completeDelivery(int deliveryId) async {
    try {
      isLoading.value = true;
      print('🚚 Completing delivery: $deliveryId');

      final response = await DriverApiService.completeDelivery(deliveryId);

      print('✅ Delivery completed: $response');
      print('✅ Backend response data: ${response.toString()}');

      // Wait a moment for backend to process the update
      await Future.delayed(Duration(milliseconds: 500));

      // Refresh the customer tracking status
      try {
        if (Get.isRegistered<CustomerDeliveryTrackingService>()) {
          print('🔄 Refreshing customer tracking status for delivery: $deliveryId');
          await CustomerDeliveryTrackingService.to.refreshStatus(deliveryId);
          print('🔄 Customer tracking status refreshed after completing delivery');
        } else {
          print('⚠️ CustomerDeliveryTrackingService not registered');
        }
      } catch (refreshError) {
        print('⚠️ Failed to refresh tracking status: $refreshError');
        // Don't fail the whole operation if refresh fails
      }

      Get.snackbar(
        'Success',
        'Delivery completed successfully!',
        backgroundColor: Colors.green,
        colorText: Colors.white,
      );
    } catch (e) {
      print('❌ Complete delivery failed: $e');
      Get.snackbar(
        'Error',
        'Failed to complete delivery: ${e.toString()}',
        backgroundColor: Colors.red,
        colorText: Colors.white,
      );
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> cancelDelivery({
    required int deliveryId,
    String? cancellationReason,
    double? rating,
    String? review,
  }) async {
    try {
      isLoading.value = true;
      print('❌ Cancelling delivery: $deliveryId');

      final response = await DriverApiService.cancelDelivery(
        deliveryId: deliveryId,
        cancellationReason: cancellationReason,
        rating: rating,
        review: review,
      );

      print('✅ Delivery cancelled: $response');

      isLoading.value = false;

      // Close dialogs and navigate back
      Navigator.of(Get.context!, rootNavigator: true).pop(); // Close feedback dialog
      Future.delayed(Duration(milliseconds: 300), () {
        Navigator.of(Get.context!, rootNavigator: true).pop(); // Close booking screen

        // Show success message
        ScaffoldMessenger.of(Get.context!).showSnackBar(
          SnackBar(
            content: Text('Delivery cancelled successfully!'),
            backgroundColor: Colors.orange,
            duration: Duration(seconds: 3),
          ),
        );
      });
    } catch (e) {
      print('❌ Cancel delivery failed: $e');
      isLoading.value = false;

      // Close the feedback dialog and show error
      Navigator.of(Get.context!, rootNavigator: true).pop();

      Future.delayed(Duration(milliseconds: 500), () {
        showDialog(
          context: Get.context!,
          barrierDismissible: false,
          builder: (context) => AlertDialog(
            title: Text('Cannot Cancel Delivery'),
            content: Text(
              e.toString(),
              textAlign: TextAlign.center,
            ),
            actions: [
              TextButton(
                onPressed: () {
                  Navigator.of(context).pop();
                },
                child: Text('OK'),
              ),
            ],
          ),
        );
      });
    }
  }
}
