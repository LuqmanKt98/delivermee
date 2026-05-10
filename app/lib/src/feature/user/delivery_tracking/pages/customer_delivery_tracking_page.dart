import 'package:deliver_mee/src/common/constant/app_colors.dart';
import 'package:deliver_mee/src/common/constant/app_images.dart';
import 'package:deliver_mee/src/common/services/customer_delivery_tracking_service.dart';
import 'package:deliver_mee/src/common/utils/text_widget.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:url_launcher/url_launcher.dart';

class CustomerDeliveryTrackingPage extends StatefulWidget {
  final int deliveryId;
  final Map<String, dynamic>? initialData;
  final bool viewOnly;

  const CustomerDeliveryTrackingPage({
    super.key,
    required this.deliveryId,
    this.initialData,
    this.viewOnly = false,
  });

  @override
  State<CustomerDeliveryTrackingPage> createState() =>
      _CustomerDeliveryTrackingPageState();
}

class _CustomerDeliveryTrackingPageState
    extends State<CustomerDeliveryTrackingPage> {
  late CustomerDeliveryTrackingService trackingService;

  @override
  void initState() {
    super.initState();
    trackingService = Get.find<CustomerDeliveryTrackingService>();
    _initializeTracking();
    _listenForDeliveryCompletion();
  }

  void _listenForDeliveryCompletion() {
    // Listen to status changes
    ever(trackingService.currentStatus, (status) {
      if (status.toLowerCase() == 'delivered' ||
          status.toLowerCase() == 'completed') {
        // Show dialog when delivery is completed
        _showDeliveryCompletedDialog();
      }
    });
  }

  @override
  void dispose() {
    trackingService.stopTracking();
    super.dispose();
  }

  void _initializeTracking() {
    // Initialize with initial data if available
    if (widget.initialData != null) {
      trackingService.deliveryData.value = widget.initialData!;
      trackingService.driverData.value = widget.initialData!['driver'] ?? {};
    }

    // Start tracking
    trackingService.startTracking(widget.deliveryId);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.whiteColor,
      appBar: AppBar(
        backgroundColor: AppColors.whiteColor,
        elevation: 0,
        leading: IconButton(
          onPressed: () => Get.back(),
          icon: Icon(Icons.arrow_back, color: AppColors.blackColor),
        ),
        title: TextWidget(
          text: 'Track Your Delivery',
          fontSize: 18.sp,
          fontWeight: FontWeight.w600,
          color: AppColors.blackColor,
        ),
        centerTitle: true,
        actions: [
          // Refresh button
          Obx(() => IconButton(
                onPressed: trackingService.isLoading.value
                    ? null
                    : () => _refreshStatus(),
                icon: trackingService.isLoading.value
                    ? SizedBox(
                        width: 20.w,
                        height: 20.w,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor: AlwaysStoppedAnimation<Color>(
                              AppColors.primaryColor),
                        ),
                      )
                    : Icon(Icons.refresh, color: AppColors.primaryColor),
                tooltip: 'Refresh Status',
              )),
          IconButton(
            onPressed: () => _showDeliveryDetails(),
            icon: Icon(Icons.info_outline, color: AppColors.primaryColor),
            tooltip: 'Delivery Details',
          ),
        ],
      ),
      body: Obx(() {
        if (trackingService.isLoading.value &&
            trackingService.deliveryData.isEmpty) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                CircularProgressIndicator(color: AppColors.primaryColor),
                SizedBox(height: 16.h),
                TextWidget(
                  text: 'Loading delivery information...',
                  fontSize: 16.sp,
                  color: AppColors.greyTextColor,
                ),
              ],
            ),
          );
        }

        if (trackingService.error.value.isNotEmpty) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.error_outline,
                    size: 64.sp, color: AppColors.redColor),
                SizedBox(height: 16.h),
                TextWidget(
                  text: 'Error',
                  fontSize: 20.sp,
                  fontWeight: FontWeight.bold,
                  color: AppColors.redColor,
                ),
                SizedBox(height: 8.h),
                TextWidget(
                  text: trackingService.error.value,
                  fontSize: 14.sp,
                  color: AppColors.greyTextColor,
                  textAlign: TextAlign.center,
                ),
                SizedBox(height: 20.h),
                ElevatedButton(
                  onPressed: () =>
                      trackingService.startTracking(widget.deliveryId),
                  child: TextWidget(
                    text: 'Retry',
                    fontSize: 14.sp,
                    color: AppColors.whiteColor,
                  ),
                ),
              ],
            ),
          );
        }

        return SingleChildScrollView(
          padding: EdgeInsets.all(16.w),
          child: Column(
            children: [
              // Map placeholder
              _buildMapSection(),

              SizedBox(height: 20.h),

              // Delivery status card
              _buildStatusCard(),

              SizedBox(height: 20.h),

              // Driver information
              if (trackingService.isDriverAssigned) ...[
                _buildDriverCard(),
                SizedBox(height: 20.h),
              ],

              // Progress timeline
              _buildProgressTimeline(),

              SizedBox(height: 20.h),

              // Delivery details
              _buildDeliveryDetailsCard(),

              SizedBox(height: 20.h),

              // Action buttons (disabled in view-only mode)
              if (!widget.viewOnly) _buildActionButtons(),
            ],
          ),
        );
      }),
    );
  }

  Widget _buildMapSection() {
    return Container(
      height: 200.h,
      width: double.infinity,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16.r),
        color: AppColors.greyColor.withOpacity(0.1),
      ),
      child: Stack(
        children: [
          // Map placeholder
          Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16.r),
              image: DecorationImage(
                image: AssetImage(AppImages.confirmdeliverymapimg),
                fit: BoxFit.cover,
              ),
            ),
          ),

          // Status overlay
          Positioned(
            top: 16.h,
            left: 16.w,
            right: 16.w,
            child: Container(
              padding: EdgeInsets.all(12.w),
              decoration: BoxDecoration(
                color: AppColors.whiteColor.withOpacity(0.9),
                borderRadius: BorderRadius.circular(12.r),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.1),
                    blurRadius: 8,
                    offset: Offset(0, 2),
                  ),
                ],
              ),
              child: Row(
                children: [
                  Icon(
                    _getStatusIcon(),
                    color: _getStatusColor(),
                    size: 20.sp,
                  ),
                  SizedBox(width: 8.w),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        TextWidget(
                          text: trackingService.statusMessage.value,
                          fontSize: 14.sp,
                          fontWeight: FontWeight.w600,
                          color: AppColors.blackColor,
                        ),
                        TextWidget(
                          text: trackingService.subStatusMessage.value,
                          fontSize: 12.sp,
                          color: AppColors.greyTextColor,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatusCard() {
    return Container(
      width: double.infinity,
      padding: EdgeInsets.all(20.w),
      decoration: BoxDecoration(
        color: AppColors.whiteColor,
        borderRadius: BorderRadius.circular(16.r),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              TextWidget(
                text: 'Delivery Status',
                fontSize: 18.sp,
                fontWeight: FontWeight.w600,
                color: AppColors.blackColor,
              ),
              Container(
                padding: EdgeInsets.symmetric(horizontal: 12.w, vertical: 6.h),
                decoration: BoxDecoration(
                  color: _getStatusColor().withOpacity(0.1),
                  borderRadius: BorderRadius.circular(20.r),
                ),
                child: TextWidget(
                  text: trackingService.currentStatus.value.toUpperCase(),
                  fontSize: 12.sp,
                  fontWeight: FontWeight.w600,
                  color: _getStatusColor(),
                ),
              ),
            ],
          ),

          SizedBox(height: 16.h),

          // Progress bar
          LinearProgressIndicator(
            value: trackingService.progressValue.value,
            backgroundColor: AppColors.greyColor.withOpacity(0.3),
            valueColor: AlwaysStoppedAnimation<Color>(_getStatusColor()),
            minHeight: 8.h,
          ),

          SizedBox(height: 12.h),

          TextWidget(
            text:
                '${(trackingService.progressValue.value * 100).toInt()}% Complete',
            fontSize: 14.sp,
            color: AppColors.greyTextColor,
          ),
        ],
      ),
    );
  }

  Widget _buildDriverCard() {
    return Container(
      width: double.infinity,
      padding: EdgeInsets.all(20.w),
      decoration: BoxDecoration(
        color: AppColors.primaryColor.withOpacity(0.05),
        borderRadius: BorderRadius.circular(16.r),
        border: Border.all(
          color: AppColors.primaryColor.withOpacity(0.2),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              CircleAvatar(
                radius: 25.r,
                backgroundColor: AppColors.primaryColor,
                child: TextWidget(
                  text: trackingService.driverName.value.isNotEmpty
                      ? trackingService.driverName.value[0].toUpperCase()
                      : 'D',
                  fontSize: 18.sp,
                  fontWeight: FontWeight.bold,
                  color: AppColors.whiteColor,
                ),
              ),
              SizedBox(width: 16.w),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    TextWidget(
                      text: trackingService.driverName.value.isNotEmpty
                          ? trackingService.driverName.value
                          : 'Driver',
                      fontSize: 16.sp,
                      fontWeight: FontWeight.w600,
                      color: AppColors.blackColor,
                    ),
                    SizedBox(height: 4.h),
                    Row(
                      children: [
                        Icon(Icons.star, color: Colors.amber, size: 16.sp),
                        SizedBox(width: 4.w),
                        TextWidget(
                          text: trackingService.driverRating.value,
                          fontSize: 14.sp,
                          color: AppColors.greyTextColor,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              if (trackingService.driverPhone.value.isNotEmpty)
                IconButton(
                  onPressed: () => _callDriver(),
                  icon: Icon(Icons.phone, color: AppColors.primaryColor),
                ),
            ],
          ),
          SizedBox(height: 16.h),
          Row(
            children: [
              Icon(Icons.access_time,
                  color: AppColors.primaryColor, size: 16.sp),
              SizedBox(width: 8.w),
              TextWidget(
                text:
                    'Estimated arrival: ${trackingService.estimatedArrival.value}',
                fontSize: 14.sp,
                color: AppColors.greyTextColor,
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildProgressTimeline() {
    final steps = [
      {'title': 'Order Confirmed', 'status': 'confirmed'},
      {
        'title': 'Driver Assigned',
        'status': 'accepted'
      }, // Also handles 'assigned'
      {'title': 'Item Picked Up', 'status': 'picked_up'},
      {'title': 'In Transit', 'status': 'in_transit'},
      {'title': 'Delivered', 'status': 'delivered'},
    ];

    return Obx(() {
      final currentStatus = trackingService.currentStatus.value;

      return Container(
        width: double.infinity,
        padding: EdgeInsets.all(20.w),
        decoration: BoxDecoration(
          color: AppColors.whiteColor,
          borderRadius: BorderRadius.circular(16.r),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.05),
              blurRadius: 10,
              offset: Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextWidget(
              text: 'Delivery Timeline',
              fontSize: 18.sp,
              fontWeight: FontWeight.w600,
              color: AppColors.blackColor,
            ),
            SizedBox(height: 20.h),
            ...steps.asMap().entries.map((entry) {
              final index = entry.key;
              final step = entry.value;
              final stepStatus = step['status']!;
              final normalizedCurrent = _normalizeStatus(currentStatus);
              final normalizedStep = _normalizeStatus(stepStatus);

              final isCompleted = _isStepCompleted(stepStatus, currentStatus);
              // Check if current status matches step status (with normalization)
              final isCurrent = normalizedCurrent == normalizedStep ||
                  (normalizedCurrent == 'assigned' &&
                      normalizedStep == 'accepted');

              return _buildTimelineStep(
                title: step['title']!,
                isCompleted: isCompleted,
                isCurrent: isCurrent,
                isLast: index == steps.length - 1,
              );
            }).toList(),
          ],
        ),
      );
    });
  }

  Widget _buildTimelineStep({
    required String title,
    required bool isCompleted,
    required bool isCurrent,
    required bool isLast,
  }) {
    return Row(
      children: [
        // Timeline indicator
        Column(
          children: [
            Container(
              width: 20.w,
              height: 20.w,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: isCompleted || isCurrent
                    ? AppColors.primaryColor
                    : AppColors.greyColor.withOpacity(0.3),
                border: isCurrent
                    ? Border.all(color: AppColors.primaryColor, width: 2)
                    : null,
              ),
              child: isCompleted
                  ? Icon(Icons.check, color: AppColors.whiteColor, size: 12.sp)
                  : isCurrent
                      ? Container(
                          width: 8.w,
                          height: 8.w,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: AppColors.whiteColor,
                          ),
                        )
                      : null,
            ),
            if (!isLast)
              Container(
                width: 2.w,
                height: 40.h,
                color: isCompleted
                    ? AppColors.primaryColor
                    : AppColors.greyColor.withOpacity(0.3),
              ),
          ],
        ),

        SizedBox(width: 16.w),

        // Step content
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              TextWidget(
                text: title,
                fontSize: 14.sp,
                fontWeight: isCurrent ? FontWeight.w600 : FontWeight.normal,
                color: isCompleted || isCurrent
                    ? AppColors.blackColor
                    : AppColors.greyTextColor,
              ),
              if (isCurrent)
                Obx(() => Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        SizedBox(height: 4.h),
                        TextWidget(
                          text: trackingService.subStatusMessage.value,
                          fontSize: 12.sp,
                          color: AppColors.greyTextColor,
                        ),
                      ],
                    )),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildDeliveryDetailsCard() {
    final delivery = trackingService.deliveryData;

    return Container(
      width: double.infinity,
      padding: EdgeInsets.all(20.w),
      decoration: BoxDecoration(
        color: AppColors.whiteColor,
        borderRadius: BorderRadius.circular(16.r),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextWidget(
            text: 'Delivery Details',
            fontSize: 18.sp,
            fontWeight: FontWeight.w600,
            color: AppColors.blackColor,
          ),
          SizedBox(height: 16.h),
          _buildDetailRow(
            icon: Icons.location_on,
            label: 'Pickup Address',
            value: delivery['pickup_address'] ?? 'N/A',
          ),
          SizedBox(height: 12.h),
          _buildDetailRow(
            icon: Icons.location_on,
            label: 'Dropoff Address',
            value: delivery['dropoff_address'] ?? 'N/A',
          ),
          SizedBox(height: 12.h),
          _buildDetailRow(
            icon: Icons.inventory,
            label: 'Item',
            value: delivery['item_name'] ?? 'N/A',
          ),
          if (delivery['tracking_number'] != null) ...[
            SizedBox(height: 12.h),
            _buildDetailRow(
              icon: Icons.confirmation_number,
              label: 'Tracking Number',
              value: delivery['tracking_number'],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildDetailRow({
    required IconData icon,
    required String label,
    required String value,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: AppColors.primaryColor, size: 16.sp),
        SizedBox(width: 12.w),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              TextWidget(
                text: label,
                fontSize: 12.sp,
                color: AppColors.greyTextColor,
              ),
              SizedBox(height: 2.h),
              TextWidget(
                text: value,
                fontSize: 14.sp,
                fontWeight: FontWeight.w500,
                color: AppColors.blackColor,
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildActionButtons() {
    return Column(
      children: [
        if (trackingService.isDriverAssigned &&
            trackingService.driverPhone.value.isNotEmpty)
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _callDriver,
              icon: Icon(Icons.phone, color: AppColors.whiteColor),
              label: TextWidget(
                text: 'Call Driver',
                fontSize: 16.sp,
                fontWeight: FontWeight.w600,
                color: AppColors.whiteColor,
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.primaryColor,
                padding: EdgeInsets.symmetric(vertical: 16.h),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12.r),
                ),
              ),
            ),
          ),
      ],
    );
  }

  IconData _getStatusIcon() {
    final status = trackingService.currentStatus.value.toLowerCase();
    switch (status) {
      case 'confirmed':
      case 'pending':
        return Icons.search;
      case 'assigned':
      case 'accepted':
        return Icons.person;
      case 'picked_up':
      case 'pickedup':
        return Icons.inventory;
      case 'in_transit':
      case 'in-transit':
      case 'intransit':
        return Icons.local_shipping;
      case 'delivered':
      case 'completed':
        return Icons.check_circle;
      case 'cancelled':
      case 'canceled':
        return Icons.cancel;
      default:
        return Icons.hourglass_empty;
    }
  }

  Color _getStatusColor() {
    final status = trackingService.currentStatus.value.toLowerCase();
    switch (status) {
      case 'confirmed':
      case 'pending':
        return Colors.orange;
      case 'assigned':
      case 'accepted':
        return Colors.blue;
      case 'picked_up':
      case 'pickedup':
        return Colors.purple;
      case 'in_transit':
      case 'in-transit':
      case 'intransit':
        return Colors.indigo;
      case 'delivered':
      case 'completed':
        return Colors.green;
      case 'cancelled':
      case 'canceled':
        return Colors.red;
      default:
        return AppColors.greyColor;
    }
  }

  bool _isStepCompleted(String stepStatus, String currentStatus) {
    final statusOrder = [
      'confirmed',
      'pending',
      'assigned',
      'accepted',
      'picked_up',
      'pickedup',
      'in_transit',
      'in-transit',
      'intransit',
      'delivered',
      'completed'
    ];

    // Map current status to standard format for comparison
    String normalizedCurrent = _normalizeStatus(currentStatus);
    String normalizedStep = _normalizeStatus(stepStatus);

    final currentIndex = statusOrder.indexOf(normalizedCurrent);
    final stepIndex = statusOrder.indexOf(normalizedStep);

    // If current status is not in the order, return false
    if (currentIndex == -1) {
      // Try to map to standard status
      if (normalizedCurrent == 'assigned') {
        return normalizedStep == 'confirmed' || normalizedStep == 'accepted';
      }
      return false;
    }

    // Step is completed if its index is less than or equal to current status index
    return stepIndex != -1 && stepIndex <= currentIndex;
  }

  /// Normalize status to standard format
  String _normalizeStatus(String status) {
    switch (status.toLowerCase()) {
      case 'pickedup':
      case 'picked_up':
        return 'picked_up';
      case 'in-transit':
      case 'intransit':
      case 'in_transit':
        return 'in_transit';
      case 'completed':
        return 'delivered';
      case 'canceled':
        return 'cancelled';
      case 'assigned':
        return 'accepted'; // Treat assigned same as accepted for timeline
      default:
        return status.toLowerCase();
    }
  }

  void _showDeliveryDetails() {
    // Show detailed delivery information
    Get.dialog(
      AlertDialog(
        title: TextWidget(
          text: 'Delivery Information',
          fontSize: 18.sp,
          fontWeight: FontWeight.w600,
        ),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildDetailRow(
                icon: Icons.confirmation_number,
                label: 'Delivery ID',
                value: widget.deliveryId.toString(),
              ),
              SizedBox(height: 12.h),
              _buildDetailRow(
                icon: Icons.access_time,
                label: 'Status',
                value: trackingService.currentStatus.value.toUpperCase(),
              ),
              if (trackingService.deliveryData['created_at'] != null) ...[
                SizedBox(height: 12.h),
                _buildDetailRow(
                  icon: Icons.calendar_today,
                  label: 'Order Date',
                  value: trackingService.deliveryData['created_at'],
                ),
              ],
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Get.back(),
            child: TextWidget(
              text: 'Close',
              fontSize: 14.sp,
              color: AppColors.primaryColor,
            ),
          ),
        ],
      ),
    );
  }

  void _callDriver() async {
    // Try to get phone from multiple sources
    String? phone = trackingService.driverPhone.value;

    // If not in service, try from driver data
    if (phone.isEmpty && trackingService.driverData.isNotEmpty) {
      phone = trackingService.driverData['phone']?.toString() ??
          trackingService.driverData['phone_number']?.toString() ??
          '';
    }

    // If still empty, try from delivery data
    if (phone.isEmpty && trackingService.deliveryData['driver'] != null) {
      final driver =
          trackingService.deliveryData['driver'] as Map<String, dynamic>;
      phone = driver['phone']?.toString() ??
          driver['phone_number']?.toString() ??
          '';
    }

    if (phone.isNotEmpty) {
      try {
        // Ensure phone number has + prefix for international format
        if (!phone.startsWith('+')) {
          phone = '+$phone';
        }

        final Uri phoneUri = Uri(scheme: 'tel', path: phone);
        if (await canLaunchUrl(phoneUri)) {
          await launchUrl(phoneUri);
        } else {
          Get.snackbar(
            'Error',
            'Cannot make phone calls on this device',
            backgroundColor: AppColors.redColor,
            colorText: AppColors.whiteColor,
          );
        }
      } catch (e) {
        print('❌ Error launching phone dialer: $e');
        Get.snackbar(
          'Error',
          'Failed to open phone dialer',
          backgroundColor: AppColors.redColor,
          colorText: AppColors.whiteColor,
        );
      }
    } else {
      Get.snackbar(
        'Phone Not Available',
        'Driver phone number is not available',
        backgroundColor: AppColors.redColor,
        colorText: AppColors.whiteColor,
      );
    }
  }

  void _showDeliveryCompletedDialog() {
    // Prevent multiple dialogs
    if (Get.isDialogOpen ?? false) return;

    // Get driver proof photo URL if available
    final driverPhotoUrl =
        trackingService.deliveryData['driver_item_photo_url'];
    final deliveryId = trackingService.deliveryData['id'];

    Future.delayed(Duration(seconds: 1), () {
      Get.dialog(
        WillPopScope(
          onWillPop: () async => false, // Prevent back button
          child: AlertDialog(
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(20.r),
            ),
            title: Column(
              children: [
                Icon(
                  Icons.check_circle,
                  color: Colors.green,
                  size: 64.sp,
                ),
                SizedBox(height: 16.h),
                TextWidget(
                  text: 'Delivery Completed!',
                  fontSize: 20.sp,
                  fontWeight: FontWeight.bold,
                  color: AppColors.blackColor,
                  textAlign: TextAlign.center,
                ),
              ],
            ),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextWidget(
                  text:
                      'Your Item has been successfully delivered. Thank you for using our service!',
                  fontSize: 14.sp,
                  color: AppColors.greyTextColor,
                  textAlign: TextAlign.center,
                ),
                // Show proof photo if available
                if (driverPhotoUrl != null &&
                    driverPhotoUrl.toString().isNotEmpty) ...[
                  SizedBox(height: 20.h),
                  TextWidget(
                    text: 'Delivery Proof Photo',
                    fontSize: 14.sp,
                    fontWeight: FontWeight.w600,
                    color: AppColors.blackColor,
                    textAlign: TextAlign.center,
                  ),
                  SizedBox(height: 12.h),
                  GestureDetector(
                    onTap: () {
                      // Open full-screen image viewer
                      if (deliveryId != null) {
                        final photoUrl =
                            'https://backend-deliver-me-ulz6fdmofq-uc.a.run.app/api/deliveries/driver-item-photo/$deliveryId/view';
                        Get.dialog(
                          Dialog(
                            backgroundColor: Colors.transparent,
                            child: Stack(
                              children: [
                                Center(
                                  child: InteractiveViewer(
                                    child: Image.network(
                                      photoUrl,
                                      fit: BoxFit.contain,
                                      loadingBuilder:
                                          (context, child, loadingProgress) {
                                        if (loadingProgress == null)
                                          return child;
                                        return Center(
                                          child: CircularProgressIndicator(
                                            color: AppColors.whiteColor,
                                          ),
                                        );
                                      },
                                      errorBuilder:
                                          (context, error, stackTrace) {
                                        return Center(
                                          child: Icon(
                                            Icons.error_outline,
                                            color: Colors.white,
                                            size: 48.sp,
                                          ),
                                        );
                                      },
                                    ),
                                  ),
                                ),
                                Positioned(
                                  top: 40.h,
                                  right: 20.w,
                                  child: IconButton(
                                    onPressed: () => Get.back(),
                                    icon: Icon(
                                      Icons.close,
                                      color: Colors.white,
                                      size: 32.sp,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        );
                      }
                    },
                    child: Container(
                      height: 150.h,
                      width: double.infinity,
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(12.r),
                        border: Border.all(
                          color: AppColors.greyTextColor.withOpacity(0.3),
                        ),
                      ),
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(12.r),
                        child: Image.network(
                          'https://backend-deliver-me-ulz6fdmofq-uc.a.run.app/api/deliveries/driver-item-photo/$deliveryId/view',
                          fit: BoxFit.cover,
                          loadingBuilder: (context, child, loadingProgress) {
                            if (loadingProgress == null) return child;
                            return Center(
                              child: CircularProgressIndicator(
                                color: AppColors.primaryColor,
                              ),
                            );
                          },
                          errorBuilder: (context, error, stackTrace) {
                            return Center(
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Icon(
                                    Icons.image_not_supported,
                                    color: AppColors.greyTextColor,
                                    size: 32.sp,
                                  ),
                                  SizedBox(height: 8.h),
                                  TextWidget(
                                    text: 'Photo not available',
                                    fontSize: 12.sp,
                                    color: AppColors.greyTextColor,
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
                      ),
                    ),
                  ),
                  SizedBox(height: 8.h),
                  TextWidget(
                    text: 'Tap to view full size',
                    fontSize: 12.sp,
                    color: AppColors.greyTextColor,
                    textAlign: TextAlign.center,
                  ),
                ],
              ],
            ),
            actions: [
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () {
                    Get.back(); // Close dialog
                    Get.until(
                        (route) => route.isFirst); // Go back to home/first page
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.primaryColor,
                    padding: EdgeInsets.symmetric(vertical: 16.h),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12.r),
                    ),
                  ),
                  child: TextWidget(
                    text: 'Go to Home',
                    fontSize: 16.sp,
                    fontWeight: FontWeight.w600,
                    color: AppColors.whiteColor,
                  ),
                ),
              ),
            ],
          ),
        ),
        barrierDismissible: false,
      );
    });
  }

  /// Refresh delivery status manually
  Future<void> _refreshStatus() async {
    try {
      print('🔄 User triggered manual refresh');

      // Show loading indicator
      trackingService.isLoading.value = true;

      // Refresh the status
      await trackingService.refreshStatus(widget.deliveryId);

      // Show success message
      Get.snackbar(
        'Refreshed',
        'Delivery status updated',
        backgroundColor: Colors.green,
        colorText: Colors.white,
        duration: Duration(seconds: 2),
        snackPosition: SnackPosition.TOP,
        icon: Icon(Icons.check_circle, color: Colors.white),
      );
    } catch (e) {
      print('❌ Error refreshing status: $e');

      // Show error message
      Get.snackbar(
        'Refresh Failed',
        'Failed to refresh delivery status. Please try again.',
        backgroundColor: Colors.red,
        colorText: Colors.white,
        duration: Duration(seconds: 3),
        snackPosition: SnackPosition.TOP,
        icon: Icon(Icons.error_outline, color: Colors.white),
      );
    } finally {
      trackingService.isLoading.value = false;
    }
  }
}
