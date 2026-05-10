import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:deliver_mee/src/common/constant/app_colors.dart';
import 'package:deliver_mee/src/common/utils/text_widget.dart';
import 'package:deliver_mee/src/feature/driver/driver_pick_up/controller/driver_delivery_history_controller.dart';

class DriverRecentDelivery extends StatelessWidget {
  const DriverRecentDelivery({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = Get.put(DriverDeliveryHistoryController());

    return Scaffold(
      backgroundColor: AppColors.whiteColor,
      appBar: AppBar(
        title: TextWidget(
          text: 'Delivery History',
          fontSize: 20.sp,
          fontWeight: FontWeight.w600,
        ),
        backgroundColor: AppColors.whiteColor,
        elevation: 0,
        actions: [
          Obx(() {
            return IconButton(
              icon: controller.isLoading.value
                  ? SizedBox(
                      width: 20.w,
                      height: 20.h,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(
                            AppColors.primaryColor),
                      ),
                    )
                  : Icon(Icons.refresh, color: AppColors.primaryColor),
              onPressed: controller.isLoading.value
                  ? null
                  : () => controller.refreshDeliveries(),
            );
          }),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Statistics Header
            Obx(() {
              final earnings = controller.calculateEarnings();
              final deliveredCount = controller.getDeliveredCount();
              final cancelledCount = controller.getCancelledCount();

              return Container(
                margin: EdgeInsets.all(16.w),
                padding: EdgeInsets.all(16.w),
                decoration: BoxDecoration(
                  color: AppColors.primaryColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12.r),
                  border: Border.all(
                    color: AppColors.primaryColor.withOpacity(0.2),
                  ),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: [
                    _buildStatItem(
                      icon: Icons.check_circle_outline,
                      label: 'Delivered',
                      value: deliveredCount.toString(),
                      color: Colors.green,
                    ),
                    Container(
                      height: 40.h,
                      width: 1,
                      color: Colors.grey.shade300,
                    ),
                    _buildStatItem(
                      icon: Icons.cancel_outlined,
                      label: 'Cancelled',
                      value: cancelledCount.toString(),
                      color: Colors.red,
                    ),
                    Container(
                      height: 40.h,
                      width: 1,
                      color: Colors.grey.shade300,
                    ),
                    _buildStatItem(
                      icon: Icons.attach_money,
                      label: 'Earnings',
                      value: '\$${earnings.toStringAsFixed(2)}',
                      color: AppColors.primaryColor,
                    ),
                  ],
                ),
              );
            }),

            // Delivery List
            Expanded(
              child: Obx(() {
                if (controller.isLoading.value &&
                    controller.deliveries.isEmpty) {
                  return const Center(child: CircularProgressIndicator());
                }

                if (controller.hasError.value) {
                  return Center(
                    child: Padding(
                      padding: EdgeInsets.all(24.w),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.error_outline,
                            size: 64.w,
                            color: Colors.red,
                          ),
                          SizedBox(height: 16.h),
                          TextWidget(
                            text: 'Error loading history',
                            fontSize: 18.sp,
                            fontWeight: FontWeight.w600,
                            color: Colors.red,
                          ),
                          SizedBox(height: 8.h),
                          TextWidget(
                            text: controller.errorMessage.value,
                            fontSize: 12.sp,
                            color: Colors.grey[600],
                            textAlign: TextAlign.center,
                            maxLines: 3,
                          ),
                          SizedBox(height: 24.h),
                          ElevatedButton(
                            onPressed: () => controller.refreshDeliveries(),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AppColors.primaryColor,
                              padding: EdgeInsets.symmetric(
                                horizontal: 32.w,
                                vertical: 12.h,
                              ),
                            ),
                            child: const Text('Retry'),
                          ),
                        ],
                      ),
                    ),
                  );
                }

                if (controller.deliveries.isEmpty) {
                  return Center(
                    child: Padding(
                      padding: EdgeInsets.all(24.w),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.history,
                            size: 80.w,
                            color: Colors.grey[300],
                          ),
                          SizedBox(height: 24.h),
                          TextWidget(
                            text: 'No delivery history',
                            fontSize: 20.sp,
                            fontWeight: FontWeight.w600,
                            textAlign: TextAlign.center,
                          ),
                          SizedBox(height: 12.h),
                          TextWidget(
                            text:
                                'Your completed and cancelled deliveries will appear here',
                            fontSize: 14.sp,
                            textAlign: TextAlign.center,
                            color: Colors.grey[600],
                            maxLines: 2,
                          ),
                        ],
                      ),
                    ),
                  );
                }

                return RefreshIndicator(
                  onRefresh: controller.refreshDeliveries,
                  child: ListView.separated(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: EdgeInsets.all(16.w),
                    itemCount: controller.deliveries.length +
                        (controller.hasMoreData.value ? 1 : 0),
                    separatorBuilder: (_, __) => SizedBox(height: 12.h),
                    itemBuilder: (context, index) {
                      if (index == controller.deliveries.length) {
                        if (controller.isLoading.value) {
                          return Center(
                            child: Padding(
                              padding: EdgeInsets.all(16.w),
                              child: const CircularProgressIndicator(),
                            ),
                          );
                        } else {
                          WidgetsBinding.instance.addPostFrameCallback((_) {
                            controller.loadMoreDeliveries();
                          });
                          return const SizedBox.shrink();
                        }
                      }

                      final d = controller.deliveries[index];
                      final status = d.status.toUpperCase();

                      Color statusColor;
                      switch (status) {
                        case 'DELIVERED':
                          statusColor = Colors.green;
                          break;
                        case 'CANCELLED':
                          statusColor = Colors.red;
                          break;
                        default:
                          statusColor = Colors.grey;
                      }

                      return Container(
                        padding: EdgeInsets.all(16.w),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(12.r),
                          border: Border.all(
                            color: Colors.grey.shade200,
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withOpacity(0.05),
                              blurRadius: 8,
                              offset: const Offset(0, 2),
                            ),
                          ],
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Container(
                                  padding: EdgeInsets.symmetric(
                                    horizontal: 12.w,
                                    vertical: 6.h,
                                  ),
                                  decoration: BoxDecoration(
                                    color: statusColor.withOpacity(0.1),
                                    borderRadius: BorderRadius.circular(20.r),
                                  ),
                                  child: TextWidget(
                                    text: status,
                                    fontSize: 12.sp,
                                    fontWeight: FontWeight.w600,
                                    color: statusColor,
                                  ),
                                ),
                                const Spacer(),
                                if (d.trackingNumber != null)
                                  TextWidget(
                                    text: '#${d.trackingNumber}',
                                    fontSize: 12.sp,
                                    color: Colors.grey[600],
                                  ),
                              ],
                            ),
                            SizedBox(height: 12.h),
                            Row(
                              children: [
                                Icon(
                                  Icons.person_outline,
                                  size: 16.w,
                                  color: Colors.grey[600],
                                ),
                                SizedBox(width: 8.w),
                                Expanded(
                                  child: TextWidget(
                                    text: d.customer?.fullName ?? 'Customer',
                                    fontSize: 13.sp,
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                              ],
                            ),
                            SizedBox(height: 8.h),
                            Row(
                              children: [
                                Icon(
                                  Icons.location_on_outlined,
                                  size: 16.w,
                                  color: Colors.grey[600],
                                ),
                                SizedBox(width: 8.w),
                                Expanded(
                                  child: TextWidget(
                                    text: d.pickupAddress,
                                    fontSize: 13.sp,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                              ],
                            ),
                            SizedBox(height: 8.h),
                            Row(
                              children: [
                                Icon(
                                  Icons.flag_outlined,
                                  size: 16.w,
                                  color: Colors.grey[600],
                                ),
                                SizedBox(width: 8.w),
                                Expanded(
                                  child: TextWidget(
                                    text: d.dropoffAddress,
                                    fontSize: 13.sp,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                              ],
                            ),
                            SizedBox(height: 12.h),
                            Row(
                              children: [
                                if (d.estimatedCost != null) ...[
                                  Icon(
                                    Icons.attach_money,
                                    size: 16.w,
                                    color: AppColors.primaryColor,
                                  ),
                                  TextWidget(
                                    text:
                                        '\$${d.estimatedCost!.toStringAsFixed(2)}',
                                    fontSize: 16.sp,
                                    fontWeight: FontWeight.w700,
                                    color: AppColors.primaryColor,
                                  ),
                                ],
                                const Spacer(),
                                if (d.deliveredTime != null)
                                  TextWidget(
                                    text: controller.formatDate(d.deliveredTime),
                                    fontSize: 12.sp,
                                    color: Colors.grey[600],
                                  ),
                              ],
                            ),
                            if (d.itemName.isNotEmpty) ...[
                              SizedBox(height: 8.h),
                              TextWidget(
                                text: 'Item: ${d.itemName}',
                                fontSize: 12.sp,
                                color: Colors.grey[700],
                              ),
                            ],
                            // Show scheduled date and time slot if available
                            if (d.scheduledDate != null || d.timeSlot != null) ...[
                              SizedBox(height: 12.h),
                              Container(
                                padding: EdgeInsets.all(8.w),
                                decoration: BoxDecoration(
                                  color: AppColors.primaryColor.withOpacity(0.1),
                                  borderRadius: BorderRadius.circular(8.r),
                                ),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    if (d.scheduledDate != null && d.scheduledDate!.isNotEmpty) ...[
                                      Row(
                                        children: [
                                          Icon(
                                            Icons.calendar_today,
                                            size: 14.sp,
                                            color: AppColors.primaryColor,
                                          ),
                                          SizedBox(width: 6.w),
                                          TextWidget(
                                            text: 'Scheduled: ${_formatScheduledDate(d.scheduledDate)}',
                                            fontSize: 11.sp,
                                            fontWeight: FontWeight.w500,
                                            color: AppColors.primaryColor,
                                          ),
                                        ],
                                      ),
                                    ],
                                    if (d.timeSlot != null && d.timeSlot!.isNotEmpty) ...[
                                      if (d.scheduledDate != null && d.scheduledDate!.isNotEmpty) SizedBox(height: 4.h),
                                      Row(
                                        children: [
                                          Icon(
                                            Icons.access_time,
                                            size: 14.sp,
                                            color: AppColors.primaryColor,
                                          ),
                                          SizedBox(width: 6.w),
                                          TextWidget(
                                            text: 'Slot: ${_formatTimeSlot(d.timeSlot)}',
                                            fontSize: 11.sp,
                                            fontWeight: FontWeight.w500,
                                            color: AppColors.primaryColor,
                                          ),
                                        ],
                                      ),
                                    ],
                                  ],
                                ),
                              ),
                            ],
                          ],
                        ),
                      );
                    },
                  ),
                );
              }),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatItem({
    required IconData icon,
    required String label,
    required String value,
    required Color color,
  }) {
    return Column(
      children: [
        Icon(icon, color: color, size: 24.sp),
        SizedBox(height: 4.h),
        TextWidget(
          text: value,
          fontSize: 16.sp,
          fontWeight: FontWeight.w700,
          color: color,
        ),
        TextWidget(
          text: label,
          fontSize: 11.sp,
          fontWeight: FontWeight.w400,
          color: Colors.grey[600],
        ),
      ],
    );
  }

  String _formatScheduledDate(String? dateStr) {
    if (dateStr == null || dateStr.isEmpty) return 'N/A';
    try {
      final dateOnly = dateStr.split('T')[0];
      final dateTime = DateTime.parse(dateOnly);
      final weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
      final months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      final weekday = weekdays[dateTime.weekday - 1];
      final month = months[dateTime.month - 1];
      return '$weekday, ${dateTime.day} $month';
    } catch (e) {
      return dateStr;
    }
  }

  String _formatTimeSlot(String? timeSlot) {
    if (timeSlot == null || timeSlot.isEmpty) return 'N/A';
    try {
      final parts = timeSlot.split('-');
      if (parts.length == 2) {
        String formatTime(String time24) {
          final hour = int.parse(time24.split(':')[0]);
          if (hour == 0) return '12:00 AM';
          if (hour < 12) return '$hour:00 AM';
          if (hour == 12) return '12:00 PM';
          return '${hour - 12}:00 PM';
        }
        return '${formatTime(parts[0])} - ${formatTime(parts[1])}';
      }
      return timeSlot;
    } catch (e) {
      return timeSlot;
    }
  }
}
