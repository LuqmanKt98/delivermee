import Flutter
import UIKit
import GoogleMaps
import Firebase
import StripePaymentSheet

@main
@objc class AppDelegate: FlutterAppDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    // Initialize Firebase
    FirebaseApp.configure()
    // Initialize Google Maps SDK
    GMSServices.provideAPIKey("AIzaSyAPePrLwHCK8ngZkELSCvETUk-B5FDUvIk")
    // Initialize Stripe
    StripeAPI.defaultPublishableKey = "pk_test_51TSMMUR2iMlLlBpEIsC374Ws6XZDTFJ19WDTB0GDt1Y2t2bWcx9YKoNzsjVAaYYlvAqoWrt3kW3S4hcqebuLmnUy00wK0UTWWy"
    GeneratedPluginRegistrant.register(with: self)
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }
}
