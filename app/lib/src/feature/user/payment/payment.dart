import 'dart:async';
import 'package:deliver_mee/src/common/constant/app_colors.dart';
import 'package:deliver_mee/src/common/utils/custom_app_bar.dart';
import 'package:deliver_mee/src/common/utils/custom_button.dart';
import 'package:deliver_mee/src/common/utils/text_widget.dart';
import 'package:deliver_mee/src/feature/user/payment/controller.dart';
import 'package:deliver_mee/src/feature/user/home/controller/controller.dart';
import 'package:deliver_mee/src/common/services/pricing_service.dart';
import 'package:deliver_mee/src/common/services/payment_service.dart';
import 'package:deliver_mee/src/common/constant/stripe_config.dart';
import 'package:deliver_mee/src/feature/user/payment/payment_success.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';

class PaymentMethodScreen extends StatefulWidget {
  const PaymentMethodScreen({super.key});

  @override
  State<PaymentMethodScreen> createState() => _PaymentMethodScreenState();
}

class _PaymentMethodScreenState extends State<PaymentMethodScreen> {
  final PaymentMethodController controller =
      Get.find<PaymentMethodController>();
  final HomeController homeController = Get.find<HomeController>();
  final PricingService pricingService = Get.find<PricingService>();

  StreamSubscription? _fromLocationSub;
  StreamSubscription? _toLocationSub;

  @override
  void initState() {
    super.initState();

    // Debug: Print current location values
    print(
        '📍 Payment Screen Init - FROM: ${homeController.fromlocation.value}');
    print('📍 Payment Screen Init - TO: ${homeController.tolocation.value}');

    // IMPORTANT:
    // Avoid mutating GetX Rx values synchronously during route transitions/build.
    // This prevents: "setState() or markNeedsBuild() called during build."
    WidgetsBinding.instance.addPostFrameCallback((_) {
      // Ensure locations are properly set for payment screen
      homeController.ensureLocationsForPayment();

      // Refresh locations to ensure they're up to date
      _refreshLocations();

      // Don't reset pricing state - it should already have the estimated cost from delivery creation
      // Only calculate fare if we don't already have valid pricing
      _calculateFare();
    });

    // Listen to location changes and recalculate fare
    _fromLocationSub = homeController.fromlocation.listen((_) {
      print(
          '📍 Payment Screen - FROM location changed to: ${homeController.fromlocation.value}');
      _calculateFare();
    });
    _toLocationSub = homeController.tolocation.listen((_) {
      print(
          '📍 Payment Screen - TO location changed to: ${homeController.tolocation.value}');
      _calculateFare();
    });
  }

  @override
  void dispose() {
    _fromLocationSub?.cancel();
    _toLocationSub?.cancel();
    super.dispose();
  }

  /// Calculate fallback fare when API fails
  void _calculateFallbackFare(double distance) {
    // Simple fallback calculation
    final baseFare = 5.0;
    final distanceRate = 2.0; // $2 per km
    final totalFare = baseFare + (distance * distanceRate);

    pricingService.baseFare.value = baseFare;
    pricingService.distanceFare.value = distance * distanceRate;
    pricingService.timeFare.value = 0.0;
    pricingService.totalFare.value = totalFare;
    pricingService.pricingError.value =
        'Using estimated fare (API unavailable)';

    print('💰 Fallback fare calculated: \$${totalFare.toStringAsFixed(2)}');
  }

  /// Test API connection and pricing
  Future<void> _testApiConnection() async {
    print('🧪 Testing API connection...');
    final isConnected = await pricingService.testApiConnection();
    print('🔗 API Connection Test Result: $isConnected');
  }

  /// Test PaymentService registration and availability
  void _testPaymentService() {
    print('🧪 Testing PaymentService...');

    try {
      if (Get.isRegistered<PaymentService>()) {
        print('✅ PaymentService is registered');

        final paymentService = Get.find<PaymentService>();
        print('✅ PaymentService instance retrieved successfully');
        print('🔍 PaymentService baseUrl: ${paymentService.baseUrl}');

        Get.snackbar(
          'Payment Service Test',
          'PaymentService is working correctly!',
          backgroundColor: Colors.green,
          colorText: Colors.white,
        );
      } else {
        print('❌ PaymentService is NOT registered');

        Get.snackbar(
          'Payment Service Test',
          'PaymentService is NOT registered! Check console for details.',
          backgroundColor: Colors.red,
          colorText: Colors.white,
        );
      }
    } catch (e) {
      print('❌ Error testing PaymentService: $e');

      Get.snackbar(
        'Payment Service Test',
        'Error testing PaymentService: $e',
        backgroundColor: Colors.red,
        colorText: Colors.white,
      );
    }
  }

  /// Create a test payment method for development
  Future<void> _createTestPaymentMethod() async {
    try {
      print('🧪 Creating test payment method...');

      final result = await controller.addPaymentMethod(
        cardNumber: StripeConfig.testCards['visa']!,
        expiryMonth: StripeConfig.testExpiryMonth,
        expiryYear: StripeConfig.testExpiryYear,
        cvv: StripeConfig.testCvc,
        cardholderName: StripeConfig.testCardholderName,
      );

      if (result['success']) {
        Get.snackbar(
          'Test Payment Method',
          'Test payment method created successfully!',
          backgroundColor: Colors.green,
          colorText: Colors.white,
        );
      } else {
        Get.snackbar(
          'Test Payment Method',
          'Failed to create test payment method: ${result['error']}',
          backgroundColor: Colors.red,
          colorText: Colors.white,
        );
      }
    } catch (e) {
      print('❌ Error creating test payment method: $e');

      Get.snackbar(
        'Test Payment Method',
        'Error creating test payment method: $e',
        backgroundColor: Colors.red,
        colorText: Colors.white,
      );
    }
  }

  /// Process payment using the payment API
  Future<void> _processPayment() async {
    try {
      print('💳 Starting payment process...');

      // Show loading dialog
      Get.dialog(
        Center(
          child: Container(
            padding: EdgeInsets.all(20.w),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12.r),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                CircularProgressIndicator(
                  valueColor:
                      AlwaysStoppedAnimation<Color>(AppColors.primaryColor),
                ),
                SizedBox(height: 16.h),
                TextWidget(
                  text: 'Processing Payment...',
                  fontSize: 16.sp,
                  fontWeight: FontWeight.w600,
                ),
              ],
            ),
          ),
        ),
        barrierDismissible: false,
      );

      // Process payment
      final result = await controller.processPayment();

      // Close loading dialog
      Get.back();

      if (result['success']) {
        // Payment successful
        print('✅ Payment successful: ${result['data']}');

        // Navigate to success screen immediately without snackbar
        Get.offAll(
          () => const PaymentSuccessScreen(),
          transition: Transition.cupertino,
        );
      } else {
        // Payment failed
        print('❌ Payment failed: ${result['error']}');

        // Handle different types of payment errors
        String errorTitle = 'Payment Failed';
        String errorMessage = result['error'] ??
            'An error occurred while processing your payment. Please try again.';

        // Check if it's a cancellation
        if (result['error']?.toLowerCase().contains('canceled') == true) {
          errorTitle = 'Payment Canceled';
          errorMessage = 'Payment was canceled. You can try again when ready.';
        } else if (result['error']?.toLowerCase().contains('network') == true) {
          errorTitle = 'Network Error';
          errorMessage = 'Please check your internet connection and try again.';
        }

        // Show error dialog
        Get.dialog(
          AlertDialog(
            title: TextWidget(
              text: errorTitle,
              fontSize: 18.sp,
              fontWeight: FontWeight.w600,
              color: Colors.red,
            ),
            content: TextWidget(
              text: errorMessage,
              fontSize: 14.sp,
            ),
            actions: [
              TextButton(
                onPressed: () => Get.back(),
                child: TextWidget(
                  text: 'OK',
                  fontSize: 14.sp,
                  color: AppColors.primaryColor,
                ),
              ),
            ],
          ),
        );
      }
    } catch (e) {
      // Close loading dialog if still open
      if (Get.isDialogOpen == true) {
        Get.back();
      }

      print('❌ Payment error: $e');

      // Show error dialog
      Get.dialog(
        AlertDialog(
          title: TextWidget(
            text: 'Payment Error',
            fontSize: 18.sp,
            fontWeight: FontWeight.w600,
            color: Colors.red,
          ),
          content: TextWidget(
            text: 'An unexpected error occurred. Please try again.',
            fontSize: 14.sp,
          ),
          actions: [
            TextButton(
              onPressed: () => Get.back(),
              child: TextWidget(
                text: 'OK',
                fontSize: 14.sp,
                color: AppColors.primaryColor,
              ),
            ),
          ],
        ),
      );
    }
  }

  /// Refresh locations from HomeController
  void _refreshLocations() {
    print('🔄 Refreshing locations from HomeController...');
    print('📍 Current FROM: ${homeController.fromlocation.value}');
    print('📍 Current TO: ${homeController.tolocation.value}');

    // Obx widgets will automatically update when location values change
    // No need for setState() since we're using reactive programming
  }

  /// Calculate fare when screen loads
  Future<void> _calculateFare() async {
    try {
      // Debug: Print current location values
      print('📍 Payment Screen - FROM: ${homeController.fromlocation.value}');
      print('📍 Payment Screen - TO: ${homeController.tolocation.value}');
      print(
          '📍 Payment Screen - FROM Coords: ${homeController.pickupLatitude.value}, ${homeController.pickupLongitude.value}');
      print(
          '📍 Payment Screen - TO Coords: ${homeController.dropoffLatitude.value}, ${homeController.dropoffLongitude.value}');

      // Check if pricing service already has a valid fare (from delivery response)
      if (pricingService.totalFare.value > 0 &&
          pricingService.pricingError.value.isEmpty) {
        print(
            '✅ Using existing fare from delivery response: \$${pricingService.totalFare.value.toStringAsFixed(2)}');
        return;
      }

      // Check if we have pricing error but still have a valid total fare
      if (pricingService.totalFare.value > 0) {
        print(
            '✅ Using existing fare despite error: \$${pricingService.totalFare.value.toStringAsFixed(2)}');
        return;
      }

      // If no valid fare exists, use default pricing
      print('⚠️ No valid fare found, using default pricing');
      pricingService.setDefaultPricing();
    } catch (e) {
      print('❌ Error calculating fare: $e');
      // Set default pricing on error
      print('⚠️ Using default pricing due to error');
      pricingService.setDefaultPricing();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CustomAppBar(text: "Payment Method", leading: true),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(16.w),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextWidget(
              text: 'Select Payment Method',
              fontSize: 20.sp,
              fontWeight: FontWeight.w600,
              color: Colors.black87,
            ),
            SizedBox(height: 20.h),

            // Apple Pay
            // _buildCheckboxTile(
            //   title: 'Apple Pay',
            //   method: PaymentMethod.applePay,
            //   icon: Icon(Icons.apple, size: 24.sp),
            // ),

            // SizedBox(height: 10.h),

            // Credit Card
            _buildCheckboxTile(
              title: 'Credit Card/Debit Card',
              method: PaymentMethod.creditCard,
              icon: Icon(Icons.credit_card_outlined, size: 24.sp),
            ),

            // SizedBox(height: 10.h),
            // Stripe
            // _buildCheckboxTile(
            //   title: 'Stripe',
            //   method: PaymentMethod.stripe,
            //   icon: Container(
            //     width: 24.w,
            //     height: 24.h,
            //     decoration: BoxDecoration(
            //       borderRadius: BorderRadius.circular(6.r),
            //       color: Colors.purple[200],
            //     ),
            //     child: Center(
            //       child: Text(
            //         'S',
            //         style: TextStyle(
            //           fontWeight: FontWeight.bold,
            //           fontSize: 16.sp,
            //           color: Colors.white,
            //         ),
            //       ),
            //     ),
            //   ),
            // ),

            SizedBox(height: 20.h),

            // Display saved payment methods
            Obx(() {
              if (controller.isLoadingPaymentMethods.value) {
                return Container(
                  padding: EdgeInsets.all(20.w),
                  child: Center(
                    child: Column(
                      children: [
                        CircularProgressIndicator(
                          valueColor: AlwaysStoppedAnimation<Color>(
                              AppColors.primaryColor),
                        ),
                        SizedBox(height: 10.h),
                        TextWidget(
                          text: 'Loading payment methods...',
                          fontSize: 14.sp,
                          color: Colors.grey[600],
                        ),
                      ],
                    ),
                  ),
                );
              }

              if (controller.availablePaymentMethods.isNotEmpty) {
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    TextWidget(
                      text: 'Saved Payment Methods',
                      fontSize: 18.sp,
                      fontWeight: FontWeight.w600,
                      color: Colors.black87,
                    ),
                    SizedBox(height: 10.h),
                    ...controller.availablePaymentMethods
                        .map((method) => _buildPaymentMethodTile(method))
                        .toList(),
                    SizedBox(height: 20.h),
                  ],
                );
              } else {
                return SizedBox.shrink();
              }
            }),

            SizedBox(height: 20.h),

            // Fare Summary
            Obx(() => Container(
                  padding: EdgeInsets.all(16.w),
                  decoration: BoxDecoration(
                    color: AppColors.primaryColor.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(12.r),
                    border: Border.all(
                        color: AppColors.primaryColor.withOpacity(0.3)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      TextWidget(
                        text: 'Delivery Summary',
                        fontSize: 18.sp,
                        fontWeight: FontWeight.w600,
                        color: AppColors.primaryColor,
                      ),
                      SizedBox(height: 12.h),

                      // Delivery ID, Tracking Number, and Price
                      Obx(() {
                        if (homeController.deliveryId.value.isNotEmpty ||
                            homeController.trackingNumber.value.isNotEmpty ||
                            homeController.deliveryPrice.value > 0) {
                          return Column(
                            children: [
                              if (homeController.deliveryId.value.isNotEmpty)
                                Row(
                                  children: [
                                    Icon(Icons.confirmation_number,
                                        color: AppColors.primaryColor,
                                        size: 16.sp),
                                    SizedBox(width: 8.w),
                                    TextWidget(
                                      text:
                                          'Delivery ID: ${homeController.deliveryId.value}',
                                      fontSize: 14.sp,
                                      fontWeight: FontWeight.w600,
                                      color: AppColors.primaryColor,
                                    ),
                                  ],
                                ),
                              if (homeController
                                  .trackingNumber.value.isNotEmpty) ...[
                                SizedBox(height: 4.h),
                                Row(
                                  children: [
                                    Icon(Icons.qr_code,
                                        color: Colors.green, size: 16.sp),
                                    SizedBox(width: 8.w),
                                    TextWidget(
                                      text:
                                          'Tracking: ${homeController.trackingNumber.value}',
                                      fontSize: 14.sp,
                                      fontWeight: FontWeight.w500,
                                      color: Colors.green[700],
                                    ),
                                  ],
                                ),
                              ],
                              SizedBox(height: 8.h),
                            ],
                          );
                        }
                        return SizedBox.shrink();
                      }),

                      // Scheduled delivery time
                      Obx(() {
                        if (homeController.scheduledTime.value.isNotEmpty) {
                          return Column(
                            children: [
                              Row(
                                children: [
                                  Icon(Icons.schedule,
                                      color: Colors.orange, size: 16.sp),
                                  SizedBox(width: 8.w),
                                  TextWidget(
                                    text:
                                        'Scheduled: ${homeController.scheduledTime.value}',
                                    fontSize: 14.sp,
                                    fontWeight: FontWeight.w500,
                                    color: Colors.orange[700],
                                  ),
                                ],
                              ),
                              SizedBox(height: 8.h),
                            ],
                          );
                        }
                        return SizedBox.shrink();
                      }),

                      // Route info - Dynamic updates
                      Obx(() {
                        print(
                            '📍 Payment screen - From location updated: ${homeController.fromlocation.value}');
                        return Row(
                          children: [
                            Icon(Icons.location_on,
                                color: AppColors.primaryColor, size: 16.sp),
                            SizedBox(width: 8.w),
                            Expanded(
                              child: TextWidget(
                                text: homeController
                                        .fromlocation.value.isNotEmpty
                                    ? 'From: ${homeController.fromlocation.value}'
                                    : 'From: Please select pickup location',
                                fontSize: 14.sp,
                                color:
                                    homeController.fromlocation.value.isNotEmpty
                                        ? Colors.black87
                                        : Colors.grey,
                              ),
                            ),
                          ],
                        );
                      }),
                      SizedBox(height: 4.h),
                      Obx(() {
                        print(
                            '📍 Payment screen - To location updated: ${homeController.tolocation.value}');
                        return Row(
                          children: [
                            Icon(Icons.location_on,
                                color: Colors.red, size: 16.sp),
                            SizedBox(width: 8.w),
                            Expanded(
                              child: TextWidget(
                                text: homeController.tolocation.value.isNotEmpty
                                    ? 'To: ${homeController.tolocation.value}'
                                    : 'To: Please select dropoff location',
                                fontSize: 14.sp,
                                color:
                                    homeController.tolocation.value.isNotEmpty
                                        ? Colors.black87
                                        : Colors.grey,
                              ),
                            ),
                          ],
                        );
                      }),
                      SizedBox(height: 12.h),

                      // Pricing breakdown
                      if (pricingService.isLoadingPricing.value)
                        Center(
                          child: Column(
                            children: [
                              CircularProgressIndicator(
                                valueColor: AlwaysStoppedAnimation<Color>(
                                    AppColors.primaryColor),
                              ),
                              SizedBox(height: 8.h),
                              TextWidget(
                                text: 'Calculating fare...',
                                fontSize: 14.sp,
                                color: Colors.grey[600],
                              ),
                            ],
                          ),
                        )
                      else if (pricingService
                          .pricingError.value.isNotEmpty) ...[
                        // Show success message with actual cost from delivery response
                        Container(
                          padding: EdgeInsets.all(12.w),
                          decoration: BoxDecoration(
                            color: Colors.green.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(8.r),
                            border: Border.all(
                                color: Colors.green.withOpacity(0.3)),
                          ),
                          child: Column(
                            children: [
                              Row(
                                children: [
                                  Icon(Icons.check_circle,
                                      color: Colors.green, size: 16.sp),
                                  SizedBox(width: 8.w),
                                  Expanded(
                                    child: TextWidget(
                                      text:
                                          'Using actual cost from delivery response',
                                      fontSize: 12.sp,
                                      color: Colors.green[800],
                                      fontWeight: FontWeight.w500,
                                    ),
                                  ),
                                ],
                              ),
                              SizedBox(height: 4.h),
                              if (homeController.deliveryId.value.isNotEmpty)
                                Row(
                                  children: [
                                    Icon(Icons.info_outline,
                                        color: Colors.blue, size: 14.sp),
                                    SizedBox(width: 8.w),
                                    Expanded(
                                      child: TextWidget(
                                        text:
                                            'Delivery ID: ${homeController.deliveryId.value}',
                                        fontSize: 11.sp,
                                        color: Colors.blue[700],
                                        fontWeight: FontWeight.w400,
                                      ),
                                    ),
                                  ],
                                ),
                              if (homeController.deliveryPrice.value > 0) ...[
                                SizedBox(height: 4.h),
                                Row(
                                  children: [
                                    Icon(Icons.attach_money,
                                        color: Colors.orange, size: 14.sp),
                                    SizedBox(width: 8.w),
                                    Expanded(
                                      child: TextWidget(
                                        text:
                                            'Delivery Price: \$${homeController.deliveryPrice.value.toStringAsFixed(2)}',
                                        fontSize: 11.sp,
                                        color: Colors.orange[700],
                                        fontWeight: FontWeight.w400,
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ],
                          ),
                        ),
                        SizedBox(height: 12.h),
                        // Show default pricing even when API fails
                        _buildPricingBreakdown(),
                      ] else ...[
                        // Base fare
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            TextWidget(text: 'Base Fare', fontSize: 14.sp),
                            TextWidget(
                              text:
                                  '\$${pricingService.baseFare.value.toStringAsFixed(2)}',
                              fontSize: 14.sp,
                              fontWeight: FontWeight.w500,
                            ),
                          ],
                        ),
                        SizedBox(height: 4.h),

                        // Distance fare
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            TextWidget(text: 'Distance Fare', fontSize: 14.sp),
                            TextWidget(
                              text:
                                  '\$${pricingService.distanceFare.value.toStringAsFixed(2)}',
                              fontSize: 14.sp,
                              fontWeight: FontWeight.w500,
                            ),
                          ],
                        ),
                        SizedBox(height: 4.h),

                        // Time fare
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            TextWidget(text: 'Time Fare', fontSize: 14.sp),
                            TextWidget(
                              text:
                                  '\$${pricingService.timeFare.value.toStringAsFixed(2)}',
                              fontSize: 14.sp,
                              fontWeight: FontWeight.w500,
                            ),
                          ],
                        ),
                        SizedBox(height: 8.h),

                        // Total fare
                        Container(
                          padding: EdgeInsets.symmetric(
                              vertical: 8.h, horizontal: 12.w),
                          decoration: BoxDecoration(
                            color: AppColors.primaryColor,
                            borderRadius: BorderRadius.circular(8.r),
                          ),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              TextWidget(
                                text: 'Total Amount',
                                fontSize: 16.sp,
                                fontWeight: FontWeight.w600,
                                color: Colors.white,
                              ),
                              TextWidget(
                                text:
                                    '\$${pricingService.totalFare.value.toStringAsFixed(2)}',
                                fontSize: 18.sp,
                                fontWeight: FontWeight.bold,
                                color: Colors.white,
                              ),
                            ],
                          ),
                        ),
                      ],
                    ],
                  ),
                )),

            SizedBox(height: 20.h),

            // Pay Now button - Use delivery price when available
            Obx(() {
              // Determine the price to display
              double displayPrice = homeController.deliveryPrice.value > 0
                  ? homeController.deliveryPrice.value
                  : pricingService.totalFare.value;

              bool isLoading = pricingService.isLoadingPricing.value ||
                  controller.paymentService.isProcessingPayment.value;

              String buttonText = isLoading
                  ? (pricingService.isLoadingPricing.value
                      ? 'Calculating...'
                      : 'Processing Payment...')
                  : 'Pay \$${displayPrice.toStringAsFixed(2)}';

              return CustomButton(
                text: buttonText,
                buttonColor: isLoading ? Colors.grey : AppColors.primaryColor,
                ontap: () {
                  if (!isLoading) {
                    _processPayment();
                  }
                },
              );
            }),
            SizedBox(height: 20.h),
            Center(
              child: TextWidget(
                text: 'Payments powered by Stripe',
                fontSize: 17.sp,
                fontWeight: FontWeight.w600,
                color: AppColors.primaryColor,
              ),
            ),
            SizedBox(height: 20.h),
          ],
        ),
      ),
    );
  }

  Widget _buildCheckboxTile({
    required String title,
    required Widget icon,
    required PaymentMethod method,
  }) {
    return Obx(() => GestureDetector(
          onTap: () => controller.selectMethod(method),
          child: Row(
            children: [
              icon,
              SizedBox(width: 10.w),
              Expanded(
                child: TextWidget(
                  text: title,
                  fontSize: 16.sp,
                  fontWeight: FontWeight.w500,
                  color: Colors.black,
                ),
              ),
              Checkbox(
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(5.r)),
                checkColor: AppColors.whiteColor,
                fillColor: WidgetStatePropertyAll(
                    controller.selectedMethod.value == method
                        ? AppColors.primaryColor
                        : AppColors.whiteColor),
                side: BorderSide(color: AppColors.blackColor),
                value: controller.selectedMethod.value == method,
                onChanged: (_) => controller.selectMethod(method),
              ),
            ],
          ),
        ));
  }

  /// Build payment method tile widget
  Widget _buildPaymentMethodTile(Map<String, dynamic> method) {
    final methodId = method['id'] ?? '';
    final isSelected = controller.selectedPaymentMethodId.value == methodId;
    final cardInfo = method['card'] ?? {};
    final brand = cardInfo['brand'] ?? 'Card';
    final last4 = cardInfo['last4'] ?? '****';
    final expMonth = cardInfo['exp_month'] ?? '';
    final expYear = cardInfo['exp_year'] ?? '';

    return Container(
      margin: EdgeInsets.only(bottom: 8.h),
      decoration: BoxDecoration(
        color:
            isSelected ? AppColors.primaryColor.withOpacity(0.1) : Colors.white,
        borderRadius: BorderRadius.circular(8.r),
        border: Border.all(
          color: isSelected ? AppColors.primaryColor : Colors.grey[300]!,
          width: isSelected ? 2 : 1,
        ),
      ),
      child: ListTile(
        leading: Container(
          width: 40.w,
          height: 25.h,
          decoration: BoxDecoration(
            color: AppColors.primaryColor,
            borderRadius: BorderRadius.circular(4.r),
          ),
          child: Center(
            child: TextWidget(
              text: brand.toUpperCase().substring(0, 1),
              fontSize: 12.sp,
              fontWeight: FontWeight.bold,
              color: Colors.white,
            ),
          ),
        ),
        title: TextWidget(
          text: '$brand ending in $last4',
          fontSize: 14.sp,
          fontWeight: FontWeight.w600,
          color: Colors.black87,
        ),
        subtitle: TextWidget(
          text: 'Expires $expMonth/$expYear',
          fontSize: 12.sp,
          color: Colors.grey[600],
        ),
        trailing: Radio<String>(
          value: methodId,
          groupValue: controller.selectedPaymentMethodId.value,
          onChanged: (value) {
            if (value != null) {
              controller.selectPaymentMethodId(value);
            }
          },
          activeColor: AppColors.primaryColor,
        ),
        onTap: () {
          controller.selectPaymentMethodId(methodId);
        },
      ),
    );
  }

  /// Build pricing breakdown widget
  Widget _buildPricingBreakdown() {
    return Column(
      children: [
        // Base fare
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            TextWidget(text: 'Base Fare', fontSize: 14.sp),
            TextWidget(
              text: '\$${pricingService.baseFare.value.toStringAsFixed(2)}',
              fontSize: 14.sp,
              fontWeight: FontWeight.w500,
            ),
          ],
        ),
        SizedBox(height: 8.h),

        // Distance fare
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            TextWidget(text: 'Distance Fare', fontSize: 14.sp),
            TextWidget(
              text: '\$${pricingService.distanceFare.value.toStringAsFixed(2)}',
              fontSize: 14.sp,
              fontWeight: FontWeight.w500,
            ),
          ],
        ),
        SizedBox(height: 8.h),

        // Time fare (if applicable)
        if (pricingService.timeFare.value > 0)
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              TextWidget(text: 'Time Fare', fontSize: 14.sp),
              TextWidget(
                text: '\$${pricingService.timeFare.value.toStringAsFixed(2)}',
                fontSize: 14.sp,
                fontWeight: FontWeight.w500,
              ),
            ],
          ),
        if (pricingService.timeFare.value > 0) SizedBox(height: 8.h),

        // Surge multiplier (if applicable)
        if (pricingService.surgeMultiplier.value > 1.0)
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              TextWidget(text: 'Surge Multiplier', fontSize: 14.sp),
              TextWidget(
                text:
                    '${pricingService.surgeMultiplier.value.toStringAsFixed(1)}x',
                fontSize: 14.sp,
                fontWeight: FontWeight.w500,
                color: Colors.orange,
              ),
            ],
          ),
        if (pricingService.surgeMultiplier.value > 1.0) SizedBox(height: 8.h),

        // Divider
        Divider(color: Colors.grey.shade300),
        SizedBox(height: 8.h),

        // Total fare
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            TextWidget(
              text: 'Total Fare',
              fontSize: 16.sp,
              fontWeight: FontWeight.w600,
              color: AppColors.primaryColor,
            ),
            TextWidget(
              text: '\$${pricingService.totalFare.value.toStringAsFixed(2)}',
              fontSize: 16.sp,
              fontWeight: FontWeight.w600,
              color: AppColors.primaryColor,
            ),
          ],
        ),
      ],
    );
  }
}
