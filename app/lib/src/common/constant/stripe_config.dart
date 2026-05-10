class StripeConfig {
  // Stripe public key for test environment
  static const String publicKey =
      'pk_test_51TSMMUR2iMlLlBpEIsC374Ws6XZDTFJ19WDTB0GDt1Y2t2bWcx9YKoNzsjVAaYYlvAqoWrt3kW3S4hcqebuLmnUy00wK0UTWWy';

  // Stripe configuration
  static const String currency = 'cad';
  static const String countryCode = 'CA';

  // Test card numbers for development (CAD compatible)
  static const Map<String, String> testCards = {
    'visa': '4242424242424242',
    'visa_debit': '4000056655665556',
    'mastercard': '5555555555554444',
    'amex': '378282246310005',
    'discover': '6011111111111117',
    'diners': '3056930009020004',
    // Canadian test cards
    'visa_ca': '4242424242424242',
    'mastercard_ca': '5555555555554444',
  };

  // Test card details
  static const String testExpiryMonth = '12';
  static const String testExpiryYear = '2025';
  static const String testCvc = '123';
  static const String testCardholderName = 'Test User';

  // Validation methods
  static bool isValidPublicKey() {
    return publicKey.startsWith('pk_test_') || publicKey.startsWith('pk_live_');
  }

  static bool isTestMode() {
    return publicKey.startsWith('pk_test_');
  }

  static String getEnvironment() {
    return isTestMode() ? 'Test' : 'Live';
  }
}
