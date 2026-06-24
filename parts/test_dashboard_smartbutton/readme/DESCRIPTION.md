**Test Module Dashboard Smart Button** is a demonstration and testing module that showcases the implementation of the DynApps Dashboard Smartbutton Mixin on the standard Odoo `res.partner` model. This module serves as both a practical example and a testing framework for developers implementing dashboard smart buttons in their own modules.

## Purpose:

- **Reference Implementation**: Provides a working example of how to integrate dashboard smart buttons into existing Odoo models
- **Testing Framework**: Validates the functionality of the dashboard smart button mixin
- **Developer Guide**: Demonstrates best practices for dashboard integration
- **Quality Assurance**: Ensures the smart button functionality works correctly with standard Odoo models

## Features:

- **Partner Dashboard Integration**: Adds dashboard smart button capability to the `res.partner` model
- **Minimal Code Example**: Shows the simplicity of integration (just inherit the mixin)
- **Test Coverage**: Provides test cases for validating smart button behavior
- **Documentation**: Serves as living documentation for the smart button feature

## What It Does:

1. Extends the standard Contacts/Partners model with dashboard smart button functionality
2. Allows any dashboard configured for the `res.partner` model to automatically appear as a smart button on partner form views
3. Enables quick access to partner-specific analytics and metrics directly from the partner record
4. Demonstrates the plug-and-play nature of the dashboard smart button mixin

## Developer Notes:

This module is categorized as "Hidden/Tests" and is intended for:
- Development and testing environments
- As a code reference for implementing dashboard smart buttons
- Validating smart button functionality before deployment
- Training and documentation purposes

The implementation is intentionally minimal to highlight how easy it is to add dashboard functionality to any model - requiring only a single line of inheritance.

## Testing Scenarios:

- Verify smart buttons appear on partner form views when dashboards are configured
- Validate that clicking buttons opens the correct dashboard with proper filtering
- Test multiple dashboard buttons on a single form view
- Ensure button_box creation when it doesn't exist in the original view
- Confirm icon and label customization works correctly
