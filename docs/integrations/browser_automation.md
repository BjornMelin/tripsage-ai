# Browser Automation Integration Guide

This document provides comprehensive instructions for integrating browser automation capabilities into TripSage for flight status checking, booking verification, and other travel-related automation tasks.

## Overview

Browser-use is a powerful automation tool that allows TripSage to interact with travel websites programmatically. The integration enables:

- Checking flight status on airline websites
- Automating flight check-in procedures
- Verifying booking details on official websites
- Capturing screenshots for verification purposes
- Monitoring price changes for flights and accommodations

The free tier offers:

- 100 automation minutes per month
- Full browser automation capabilities
- Screenshot capture
- Element selection
- No setup fees or infrastructure requirements

## Setup Instructions

### 1. Create a Browser-use Account

1. Visit [Browser-use Sign Up](https://browser-use.com/signup) and create a free account
2. Verify your email address through the confirmation link
3. Navigate to the dashboard to access your account details

### 2. Generate API Key

1. From your Browser-use dashboard, navigate to "API Keys" section
2. Click "Create API Key" and provide a name (e.g., "TripSage Personal")
3. Copy the generated API key to a secure location
4. Set usage alerts to monitor consumption (recommended at 50% and 80%)

### 3. Configure Environment Variables

Create or update the `.env` file in your TripSage project root:

```
BROWSER_USE_API_KEY=your_api_key_here
BROWSER_USE_TIMEOUT=30000
BROWSER_USE_HEADLESS=true
```

### 4. Install Required Dependencies

```bash
npm install dotenv axios
```

### Implementation

#### Basic Browser Service

Create a file `src/services/automation/browser-service.js`:

```javascript
const mcpClient = require("../../utils/mcp-client");
const { cacheWithTTL } = require("../../utils/cache");
const logger = require("../../utils/logger");

class BrowserService {
  constructor() {
    this.usageTracker = new UsageTracker();
  }

  /**
   * Check flight status on airline website
   * @param {Object} params Flight status parameters
   * @returns {Promise<Object>} Flight status information
   */
  async checkFlightStatus(params) {
    const { airline, flightNumber, date } = params;
    const estimatedDuration = 1; // Estimated minutes

    // Check if we should proceed with automation
    if (
      !this.usageTracker.shouldProceedWithTask(
        "flightStatus",
        estimatedDuration
      )
    ) {
      return {
        success: false,
        message:
          "Automation usage limit approaching. Using alternative data source.",
      };
    }

    try {
      // Record start time for usage tracking
      const startTime = Date.now();

      // Get airline website URL
      const airlineUrl = this.getAirlineStatusUrl(airline);

      // Navigate to airline status page
      await mcpClient.call("browser", "browser_navigate", {
        url: airlineUrl,
      });

      // Wait for page to load
      await mcpClient.call("browser", "browser_wait", {
        time: 3, // Wait 3 seconds
      });

      // Get page snapshot for analysis
      const snapshot = await mcpClient.call("browser", "browser_snapshot", {});

      // Fill in flight details based on airline
      if (airline === "AA") {
        // American Airlines implementation
        await this.fillAmericanAirlinesForm(snapshot, flightNumber, date);
      } else if (airline === "DL") {
        // Delta Airlines implementation
        await this.fillDeltaAirlinesForm(snapshot, flightNumber, date);
      } else {
        // Generic approach for other airlines
        await this.fillGenericFlightStatusForm(snapshot, flightNumber, date);
      }

      // Wait for results to load
      await mcpClient.call("browser", "browser_wait", {
        time: 5, // Wait 5 seconds
      });

      // Take screenshot of results
      const screenshot = await mcpClient.call("browser", "browser_screenshot", {
        name: `flight_status_${airline}_${flightNumber}`,
      });

      // Get visible text content
      const content = await mcpClient.call(
        "browser",
        "browser_get_visible_text",
        {}
      );

      // Parse flight status information
      const statusInfo = this.parseFlightStatusFromText(content, airline);

      // Record usage
      const duration = (Date.now() - startTime) / 60000; // Convert to minutes
      this.usageTracker.recordTaskUsage("flightStatus", duration);

      return {
        success: true,
        airline,
        flightNumber,
        date,
        status: statusInfo,
        screenshot,
        raw_content: content.substring(0, 1000), // Limit content size
      };
    } catch (error) {
      logger.error(
        `Error checking flight status for ${airline} ${flightNumber}:`,
        error
      );
      return {
        success: false,
        message: `Failed to check flight status: ${error.message}`,
      };
    }
  }

  /**
   * Perform flight check-in
   * @param {Object} params Check-in parameters
   * @returns {Promise<Object>} Check-in result
   */
  async checkInForFlight(params) {
    const { airline, confirmationCode, lastName, firstName, flightDate } =
      params;
    const estimatedDuration = 2; // Estimated minutes

    // Check if we should proceed with automation
    if (
      !this.usageTracker.shouldProceedWithTask("checkIn", estimatedDuration)
    ) {
      return {
        success: false,
        message:
          "Automation usage limit approaching. Please check in manually.",
      };
    }

    try {
      // Record start time for usage tracking
      const startTime = Date.now();

      // Get airline check-in URL
      const checkInUrl = this.getAirlineCheckInUrl(airline);

      // Navigate to check-in page
      await mcpClient.call("browser", "browser_navigate", {
        url: checkInUrl,
      });

      // Wait for page to load
      await mcpClient.call("browser", "browser_wait", {
        time: 3,
      });

      // Get page snapshot
      const snapshot = await mcpClient.call("browser", "browser_snapshot", {});

      // Fill in check-in details based on airline
      if (airline === "AA") {
        await this.fillAmericanAirlinesCheckIn(
          snapshot,
          confirmationCode,
          lastName,
          firstName
        );
      } else if (airline === "DL") {
        await this.fillDeltaAirlinesCheckIn(
          snapshot,
          confirmationCode,
          lastName
        );
      } else {
        await this.fillGenericCheckInForm(
          snapshot,
          confirmationCode,
          lastName,
          firstName
        );
      }

      // Wait for check-in page to load
      await mcpClient.call("browser", "browser_wait", {
        time: 5,
      });

      // Take screenshot of check-in page
      const checkInScreenshot = await mcpClient.call(
        "browser",
        "browser_screenshot",
        {
          name: `check_in_${airline}_${confirmationCode}`,
        }
      );

      // Get visible text
      const content = await mcpClient.call(
        "browser",
        "browser_get_visible_text",
        {}
      );

      // Check for common error messages
      const errorMessage = this.detectCheckInErrors(content);

      // Record usage
      const duration = (Date.now() - startTime) / 60000; // Convert to minutes
      this.usageTracker.recordTaskUsage("checkIn", duration);

      if (errorMessage) {
        return {
          success: false,
          airline,
          confirmationCode,
          error: errorMessage,
          screenshot: checkInScreenshot,
        };
      }

      // Process successful check-in
      return {
        success: true,
        airline,
        confirmationCode,
        message: "Check-in completed successfully",
        boarding_pass_available:
          content.includes("boarding pass") ||
          content.includes("Boarding Pass"),
        screenshot: checkInScreenshot,
      };
    } catch (error) {
      logger.error(`Error checking in for ${airline} flight:`, error);
      return {
        success: false,
        message: `Failed to check in: ${error.message}`,
      };
    }
  }

  /**
   * Verify a booking
   * @param {Object} params Booking verification parameters
   * @returns {Promise<Object>} Verification result
   */
  async verifyBooking(params) {
    const { type, provider, confirmationCode, lastName, firstName } = params;
    const estimatedDuration = 1.5; // Estimated minutes

    // Check if we should proceed with automation
    if (
      !this.usageTracker.shouldProceedWithTask(
        "verifyBooking",
        estimatedDuration
      )
    ) {
      return {
        success: false,
        message:
          "Automation usage limit approaching. Please verify booking manually.",
      };
    }

    try {
      // Record start time for usage tracking
      const startTime = Date.now();

      // Get verification URL based on booking type and provider
      const verificationUrl = this.getBookingVerificationUrl(type, provider);

      // Navigate to verification page
      await mcpClient.call("browser", "browser_navigate", {
        url: verificationUrl,
      });

      // Wait for page to load
      await mcpClient.call("browser", "browser_wait", {
        time: 3,
      });

      // Get page snapshot
      const snapshot = await mcpClient.call("browser", "browser_snapshot", {});

      // Fill verification form based on type and provider
      if (type === "flight") {
        await this.fillFlightVerificationForm(
          snapshot,
          provider,
          confirmationCode,
          lastName
        );
      } else if (type === "hotel") {
        await this.fillHotelVerificationForm(
          snapshot,
          provider,
          confirmationCode,
          lastName
        );
      } else if (type === "car") {
        await this.fillCarRentalVerificationForm(
          snapshot,
          provider,
          confirmationCode,
          lastName
        );
      }

      // Wait for verification page to load
      await mcpClient.call("browser", "browser_wait", {
        time: 5,
      });

      // Take screenshot of verification page
      const verificationScreenshot = await mcpClient.call(
        "browser",
        "browser_screenshot",
        {
          name: `verify_${type}_${provider}_${confirmationCode}`,
        }
      );

      // Get visible text
      const content = await mcpClient.call(
        "browser",
        "browser_get_visible_text",
        {}
      );

      // Extract booking details
      const bookingDetails = this.extractBookingDetails(
        content,
        type,
        provider
      );

      // Record usage
      const duration = (Date.now() - startTime) / 60000; // Convert to minutes
      this.usageTracker.recordTaskUsage("verifyBooking", duration);

      return {
        success: true,
        type,
        provider,
        confirmationCode,
        details: bookingDetails,
        screenshot: verificationScreenshot,
      };
    } catch (error) {
      logger.error(`Error verifying ${type} booking with ${provider}:`, error);
      return {
        success: false,
        message: `Failed to verify booking: ${error.message}`,
      };
    }
  }

  /**
   * Monitor price for a booking
   * @param {Object} params Price monitoring parameters
   * @returns {Promise<Object>} Price monitoring result
   */
  async monitorPrice(params) {
    const { type, provider, origin, destination, date, returnDate, travelers } =
      params;
    const estimatedDuration = 1.5; // Estimated minutes

    // Check if we should proceed with automation
    if (
      !this.usageTracker.shouldProceedWithTask(
        "monitorPrice",
        estimatedDuration
      )
    ) {
      return {
        success: false,
        message:
          "Automation usage limit approaching. Using alternative price source.",
      };
    }

    try {
      // Record start time for usage tracking
      const startTime = Date.now();

      // Get search URL based on booking type and provider
      const searchUrl = this.getSearchUrl(type, provider);

      // Navigate to search page
      await mcpClient.call("browser", "browser_navigate", {
        url: searchUrl,
      });

      // Wait for page to load
      await mcpClient.call("browser", "browser_wait", {
        time: 3,
      });

      // Get page snapshot
      const snapshot = await mcpClient.call("browser", "browser_snapshot", {});

      // Fill search form based on type and provider
      if (type === "flight") {
        await this.fillFlightSearchForm(
          snapshot,
          provider,
          origin,
          destination,
          date,
          returnDate,
          travelers
        );
      } else if (type === "hotel") {
        await this.fillHotelSearchForm(
          snapshot,
          provider,
          destination,
          date,
          returnDate,
          travelers
        );
      }

      // Wait for search results to load
      await mcpClient.call("browser", "browser_wait", {
        time: 8, // Longer wait for search results
      });

      // Take screenshot of search results
      const searchScreenshot = await mcpClient.call(
        "browser",
        "browser_screenshot",
        {
          name: `price_${type}_${provider}_${origin || ""}_${destination}`,
        }
      );

      // Get visible text
      const content = await mcpClient.call(
        "browser",
        "browser_get_visible_text",
        {}
      );

      // Extract price information
      const priceInfo = this.extractPriceInfo(content, type, provider);

      // Record usage
      const duration = (Date.now() - startTime) / 60000; // Convert to minutes
      this.usageTracker.recordTaskUsage("monitorPrice", duration);

      return {
        success: true,
        type,
        provider,
        search: {
          origin: origin || null,
          destination,
          date,
          returnDate: returnDate || null,
          travelers,
        },
        prices: priceInfo,
        screenshot: searchScreenshot,
      };
    } catch (error) {
      logger.error(`Error monitoring ${type} prices with ${provider}:`, error);
      return {
        success: false,
        message: `Failed to monitor prices: ${error.message}`,
      };
    }
  }

  // Helper methods and form-filling implementations
  // (Implementation details omitted for brevity)
}

/**
 * Automation usage tracking for Browser-use
 */
class UsageTracker {
  constructor() {
    this.monthlyLimit = 100; // Free tier (minutes)
    this.minutesUsed = 0;
    this.tasks = [];
    this.loadSavedUsage();
  }

  loadSavedUsage() {
    try {
      const savedUsage = JSON.parse(localStorage.getItem("browser_use_usage"));
      if (savedUsage && new Date(savedUsage.resetDate) > new Date()) {
        this.minutesUsed = savedUsage.minutesUsed;
        this.tasks = savedUsage.tasks;
      } else {
        // Reset for new month
        this.resetUsage();
      }
    } catch (error) {
      logger.error("Error loading automation usage:", error);
      this.resetUsage();
    }
  }

  resetUsage() {
    this.minutesUsed = 0;
    this.tasks = [];

    // Set reset date to first day of next month
    const now = new Date();
    const resetDate = new Date(now.getFullYear(), now.getMonth() + 1, 1);

    this.saveUsage(resetDate);
  }

  saveUsage(resetDate) {
    try {
      const resetDateToUse =
        resetDate ||
        new Date(new Date().getFullYear(), new Date().getMonth() + 1, 1);

      localStorage.setItem(
        "browser_use_usage",
        JSON.stringify({
          minutesUsed: this.minutesUsed,
          tasks: this.tasks,
          resetDate: resetDateToUse.toISOString(),
        })
      );
    } catch (error) {
      logger.error("Error saving automation usage:", error);
    }
  }

  recordTaskUsage(taskType, durationMinutes) {
    this.minutesUsed += durationMinutes;
    this.tasks.push({
      type: taskType,
      duration: durationMinutes,
      timestamp: new Date().toISOString(),
    });

    this.saveUsage();

    return {
      minutesUsed: this.minutesUsed,
      minutesRemaining: this.monthlyLimit - this.minutesUsed,
    };
  }

  shouldProceedWithTask(taskType, estimatedDuration) {
    const remainingMinutes = this.monthlyLimit - this.minutesUsed;

    // Always allow check-ins as they're time-sensitive
    if (taskType === "checkIn") {
      return remainingMinutes >= estimatedDuration;
    }

    // For other tasks, be more conservative
    if (remainingMinutes < 15) {
      return false;
    }

    if (remainingMinutes < 30) {
      // Only allow important task types when under 30 minutes
      return ["checkIn", "verifyBooking"].includes(taskType);
    }

    return true;
  }

  getRemainingMinutes() {
    return this.monthlyLimit - this.minutesUsed;
  }

  getUsageSummary() {
    // Calculate usage metrics
    const taskTypeCounts = this.tasks.reduce((counts, task) => {
      counts[task.type] = (counts[task.type] || 0) + 1;
      return counts;
    }, {});

    const taskTypeMinutes = this.tasks.reduce((minutes, task) => {
      minutes[task.type] = (minutes[task.type] || 0) + task.duration;
      return minutes;
    }, {});

    return {
      minutesUsed: this.minutesUsed,
      minutesRemaining: this.monthlyLimit - this.minutesUsed,
      percentageUsed: (this.minutesUsed / this.monthlyLimit) * 100,
      taskCounts: taskTypeCounts,
      taskMinutes: taskTypeMinutes,
      recentTasks: this.tasks.slice(-5), // Last 5 tasks
    };
  }
}

module.exports = new BrowserService();
```

#### Browser Utility Functions

Create a file `src/utils/browser-utils.js`:

```javascript
/**
 * Utility functions for browser automation
 */
const browserUtils = {
  /**
   * Format date for travel websites
   * @param {string} date ISO date string (YYYY-MM-DD)
   * @param {string} format Target format (MM/DD/YYYY, DD/MM/YYYY, etc.)
   * @returns {string} Formatted date
   */
  formatDate(date, format) {
    const dateObj = new Date(date);
    if (isNaN(dateObj.getTime())) {
      throw new Error(`Invalid date: ${date}`);
    }

    const day = dateObj.getDate().toString().padStart(2, "0");
    const month = (dateObj.getMonth() + 1).toString().padStart(2, "0");
    const year = dateObj.getFullYear();

    switch (format) {
      case "MM/DD/YYYY":
        return `${month}/${day}/${year}`;
      case "DD/MM/YYYY":
        return `${day}/${month}/${year}`;
      case "YYYY-MM-DD":
        return `${year}-${month}-${day}`;
      default:
        return date;
    }
  },

  /**
   * Get URL for airline flight status page
   * @param {string} airline Airline code
   * @returns {string} URL
   */
  getAirlineStatusUrl(airline) {
    const airlineUrls = {
      AA: "https://www.aa.com/travelInformation/flights/status",
      DL: "https://www.delta.com/flight-status-lookup",
      UA: "https://www.united.com/en/us/flightstatus",
      WN: "https://www.southwest.com/air/flight-status",
      // Add more airlines as needed
    };

    return (
      airlineUrls[airline] ||
      `https://www.google.com/search?q=${airline}+flight+status`
    );
  },

  /**
   * Find an element in a page snapshot
   * @param {Object} snapshot Page snapshot
   * @param {string} elementType Element type (input, button, etc.)
   * @param {string} nameHint Name hint to match against attributes
   * @returns {Object|null} Matching element or null
   */
  findElement(snapshot, elementType, nameHint) {
    if (!snapshot || !snapshot.nodes) {
      return null;
    }

    const matchingElements = snapshot.nodes.filter((node) => {
      if (node.type !== "element") return false;

      // Check if element type matches
      const isMatchingType = elementType.includes("[")
        ? node.tagName.toLowerCase() === elementType.split("[")[0] &&
          node.attributes.some(
            (attr) =>
              attr.name === elementType.split("[")[1].split("=")[0].trim()
          )
        : node.tagName.toLowerCase() === elementType;

      if (!isMatchingType) return false;

      // Check if element has matching attributes
      const hasMatchingAttr = node.attributes.some((attr) => {
        const attrValue = attr.value || "";
        return (
          (attr.name === "name" ||
            attr.name === "id" ||
            attr.name === "placeholder") &&
          attrValue.toLowerCase().includes(nameHint.toLowerCase())
        );
      });

      // Check for aria-label as well
      const hasMatchingAriaLabel = node.attributes.some(
        (attr) =>
          attr.name === "aria-label" &&
          attr.value.toLowerCase().includes(nameHint.toLowerCase())
      );

      return hasMatchingAttr || hasMatchingAriaLabel;
    });

    return matchingElements.length > 0 ? matchingElements[0] : null;
  },

  /**
   * Detect error messages in text content
   * @param {string} content Text content to analyze
   * @param {Array} errorPatterns Patterns to search for
   * @returns {string|null} Error message or null
   */
  detectErrors(content, errorPatterns) {
    if (!content || !errorPatterns || !errorPatterns.length) {
      return null;
    }

    for (const pattern of errorPatterns) {
      if (pattern.regex.test(content)) {
        return pattern.message;
      }
    }

    return null;
  },
};

module.exports = browserUtils;
```

#### Security Utility

Create a file `src/utils/security-utils.js`:

```javascript
/**
 * Security utilities for browser automation
 */
const securityUtils = {
  /**
   * Mask sensitive information in logs and responses
   * @param {string} text Text containing sensitive information
   * @param {Array} patterns Patterns to mask (e.g., confirmation numbers)
   * @returns {string} Text with masked information
   */
  maskSensitiveInfo(text, patterns) {
    if (!text) return text;

    let maskedText = text;

    // Mask common patterns
    const defaultPatterns = [
      { regex: /\b[A-Z0-9]{6}\b/g, replacement: "******" }, // Confirmation codes
      {
        regex: /\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/g,
        replacement: "****************",
      }, // Credit cards
      { regex: /\b[A-Z]{2}\d{6}\b/g, replacement: "********" }, // Passport numbers
    ];

    const allPatterns = [...defaultPatterns, ...(patterns || [])];

    // Apply masking
    allPatterns.forEach((pattern) => {
      maskedText = maskedText.replace(pattern.regex, pattern.replacement);
    });

    return maskedText;
  },

  /**
   * Validate user input for security concerns
   * @param {Object} params Input parameters
   * @param {Array} validationRules Validation rules to apply
   * @returns {Object} Validation result {valid: boolean, errors: Array}
   */
  validateUserInput(params, validationRules) {
    const result = {
      valid: true,
      errors: [],
    };

    if (!params || !validationRules) {
      result.valid = false;
      result.errors.push("Invalid parameters or validation rules");
      return result;
    }

    for (const rule of validationRules) {
      const { field, type, pattern, message, required } = rule;

      // Check required fields
      if (
        required &&
        (params[field] === undefined ||
          params[field] === null ||
          params[field] === "")
      ) {
        result.valid = false;
        result.errors.push(message || `${field} is required`);
        continue;
      }

      // Skip validation if field is not present and not required
      if (!params[field] && !required) {
        continue;
      }

      // Validate by type
      if (type === "string" && typeof params[field] !== "string") {
        result.valid = false;
        result.errors.push(message || `${field} must be a string`);
      }

      // Validate by pattern
      if (pattern && !pattern.test(params[field])) {
        result.valid = false;
        result.errors.push(message || `${field} has invalid format`);
      }
    }

    return result;
  },
};

module.exports = securityUtils;
```

#### API Routes

Create a file `src/api/routes/automation.js`:

```javascript
const express = require("express");
const router = express.Router();
const browserService = require("../../services/automation/browser-service");
const securityUtils = require("../../utils/security-utils");
const { asyncHandler } = require("../../utils/error");

/**
 * Input validation rules
 */
const validationRules = {
  flightStatus: [
    {
      field: "airline",
      type: "string",
      pattern: /^[A-Z0-9]{2,3}$/,
      message: "Airline code must be 2-3 characters",
      required: true,
    },
    {
      field: "flightNumber",
      type: "string",
      pattern: /^\d{1,4}[A-Z]?$/,
      message: "Invalid flight number format",
      required: true,
    },
    {
      field: "date",
      type: "string",
      pattern: /^\d{4}-\d{2}-\d{2}$/,
      message: "Date must be in YYYY-MM-DD format",
      required: true,
    },
  ],

  checkIn: [
    {
      field: "airline",
      type: "string",
      pattern: /^[A-Z0-9]{2,3}$/,
      message: "Airline code must be 2-3 characters",
      required: true,
    },
    {
      field: "confirmationCode",
      type: "string",
      pattern: /^[A-Z0-9]{6}$/,
      message: "Confirmation code must be 6 characters",
      required: true,
    },
    { field: "lastName", type: "string", required: true },
  ],

  verifyBooking: [
    {
      field: "type",
      type: "string",
      pattern: /^(flight|hotel|car)$/,
      message: "Type must be flight, hotel, or car",
      required: true,
    },
    { field: "provider", type: "string", required: true },
    { field: "confirmationCode", type: "string", required: true },
    { field: "lastName", type: "string", required: true },
  ],
};

/**
 * @route   GET /api/automation/flight-status
 * @desc    Check flight status
 * @access  Public
 */
router.get(
  "/flight-status",
  asyncHandler(async (req, res) => {
    // Validate input
    const validation = securityUtils.validateUserInput(
      req.query,
      validationRules.flightStatus
    );
    if (!validation.valid) {
      return res.status(400).json({
        error: validation.errors.join(", "),
      });
    }

    const { airline, flightNumber, date } = req.query;

    const status = await browserService.checkFlightStatus({
      airline,
      flightNumber,
      date,
    });

    res.json(status);
  })
);

/**
 * @route   POST /api/automation/check-in
 * @desc    Perform flight check-in
 * @access  Public
 */
router.post(
  "/check-in",
  asyncHandler(async (req, res) => {
    // Validate input
    const validation = securityUtils.validateUserInput(
      req.body,
      validationRules.checkIn
    );
    if (!validation.valid) {
      return res.status(400).json({
        error: validation.errors.join(", "),
      });
    }

    const { airline, confirmationCode, lastName, firstName, flightDate } =
      req.body;

    const checkInResult = await browserService.checkInForFlight({
      airline,
      confirmationCode,
      lastName,
      firstName,
      flightDate,
    });

    res.json(checkInResult);
  })
);

/**
 * @route   POST /api/automation/verify-booking
 * @desc    Verify booking details
 * @access  Public
 */
router.post(
  "/verify-booking",
  asyncHandler(async (req, res) => {
    // Validate input
    const validation = securityUtils.validateUserInput(
      req.body,
      validationRules.verifyBooking
    );
    if (!validation.valid) {
      return res.status(400).json({
        error: validation.errors.join(", "),
      });
    }

    const { type, provider, confirmationCode, lastName, firstName } = req.body;

    const verificationResult = await browserService.verifyBooking({
      type,
      provider,
      confirmationCode,
      lastName,
      firstName,
    });

    res.json(verificationResult);
  })
);

/**
 * @route   GET /api/automation/usage
 * @desc    Get automation usage statistics
 * @access  Public
 */
router.get(
  "/usage",
  asyncHandler(async (req, res) => {
    const usageSummary = browserService.usageTracker.getUsageSummary();
    res.json(usageSummary);
  })
);

module.exports = router;
```

## Usage Patterns and Optimization

### Cost-Effective Usage Strategies

The Browser-use free tier provides 100 automation minutes per month, which requires careful management for personal usage. Here are strategies to optimize usage:

1. **Selective Automation**

   - Only automate tasks that add significant value (check-ins, complex verifications)
   - Use direct API calls when possible instead of browser automation
   - Prioritize time-sensitive operations (like flight check-ins)

2. **Usage Tracking**

   - Implement the UsageTracker class to monitor minute consumption
   - Set alerts at 50% and 80% usage thresholds
   - Reset tracking on the first day of each month

3. **Efficiency Optimization**

   - Pre-check for cached data before initiating automation
   - Use browser_snapshot instead of multiple screenshots
   - Implement early termination for failed actions
   - Select optimal waiting times based on actual load patterns

4. **Fallback Mechanisms**
   - Create alternative data sources for when usage limits are approaching
   - Gracefully degrade to non-automated options
   - Cache results when appropriate to avoid redundant automations

### Example Automation Workflows

These workflows demonstrate efficient usage of browser automation for common travel tasks:

#### Flight Status Check Workflow

```javascript
// Example implementation in travel agent code
async function checkFlightStatus(airline, flightNumber, date) {
  // First try airline API if available
  const apiResult = await tryAirlineAPI(airline, flightNumber, date);
  if (apiResult.success) {
    return apiResult;
  }

  // Check cache for recent results
  const cachedResult = await checkCache("flightStatus", {
    airline,
    flightNumber,
    date,
  });
  if (cachedResult) {
    return {
      ...cachedResult,
      source: "cache",
    };
  }

  // Fall back to browser automation
  const browserResult = await browserService.checkFlightStatus({
    airline,
    flightNumber,
    date,
  });

  // Cache successful results
  if (browserResult.success) {
    await cacheResult(
      "flightStatus",
      { airline, flightNumber, date },
      browserResult,
      30
    ); // 30 minute TTL
  }

  return browserResult;
}
```

#### Booking Verification Workflow

```javascript
// Example implementation in travel agent code
async function verifyBooking(type, provider, confirmationCode, lastName) {
  // Check cache first (with short TTL)
  const cachedResult = await checkCache("bookingVerification", {
    type,
    provider,
    confirmationCode,
    lastName,
  });

  if (cachedResult) {
    return {
      ...cachedResult,
      source: "cache",
    };
  }

  // Check usage before proceeding
  const usageStats = browserService.usageTracker.getUsageSummary();
  if (usageStats.percentageUsed > 80) {
    return {
      success: false,
      message:
        "Browser automation usage limit approaching. Please verify manually using the provider's website.",
      verificationUrl: getProviderUrl(type, provider),
    };
  }

  // Proceed with browser automation
  const result = await browserService.verifyBooking({
    type,
    provider,
    confirmationCode,
    lastName,
  });

  // Cache successful results for a short period
  if (result.success) {
    await cacheResult(
      "bookingVerification",
      { type, provider, confirmationCode, lastName },
      result,
      60 // 60 minute TTL
    );
  }

  return result;
}
```

## Security Guidelines

When implementing browser automation for travel tasks, follow these security best practices:

### Personal API Key Protection

1. **Secure Storage**:

   - Never hard-code API keys in source code
   - Use environment variables or secure storage solutions
   - Limit access to your `.env` file

2. **Key Rotation**:

   - Regularly rotate your Browser-use API key (every 3-6 months)
   - Immediately invalidate keys if accidentally exposed

3. **Key Usage Scope**:
   - Use different API keys for development and production
   - Set usage alerts to detect unusual activity

### Sensitive Data Handling

1. **Data Minimization**:

   - Only request essential personal information
   - Don't store sensitive data like confirmation codes longer than necessary

2. **Data Masking**:

   - Mask confirmation codes and other sensitive data in logs
   - Use the securityUtils.maskSensitiveInfo() function

3. **Screenshot Security**:
   - Review screenshots for sensitive information before storage
   - Implement automatic redaction of sensitive data in screenshots

### Input Validation

1. **Parameter Validation**:

   - Validate all input parameters before passing to automation
   - Use the securityUtils.validateUserInput() function
   - Reject malformed or suspicious inputs

2. **Client-Side Protection**:
   - Implement client-side validation for early detection
   - Use server-side validation as the authoritative check

## Testing and Verification

### Unit Tests

Create a test file `src/tests/browser-service.test.js`:

```javascript
const browserService = require("../services/automation/browser-service");
const browserUtils = require("../utils/browser-utils");
const securityUtils = require("../utils/security-utils");

describe("Browser Service", () => {
  // Test date formatting utility
  test("browserUtils.formatDate correctly formats dates", () => {
    expect(browserUtils.formatDate("2023-05-15", "MM/DD/YYYY")).toBe(
      "05/15/2023"
    );
    expect(browserUtils.formatDate("2023-05-15", "DD/MM/YYYY")).toBe(
      "15/05/2023"
    );
    expect(browserUtils.formatDate("2023-05-15", "YYYY-MM-DD")).toBe(
      "2023-05-15"
    );
  });

  // Test security utility
  test("securityUtils.maskSensitiveInfo masks confirmation codes", () => {
    const text = "Your confirmation code is ABC123";
    expect(securityUtils.maskSensitiveInfo(text, [])).toBe(
      "Your confirmation code is ******"
    );
  });

  // Test input validation
  test("securityUtils.validateUserInput validates flight status inputs", () => {
    const validInput = {
      airline: "AA",
      flightNumber: "123",
      date: "2023-05-15",
    };

    const invalidInput = {
      airline: "AAAA", // Too long
      flightNumber: "ABC", // No number
      date: "05/15/2023", // Wrong format
    };

    const validationRules = [
      {
        field: "airline",
        type: "string",
        pattern: /^[A-Z0-9]{2,3}$/,
        required: true,
      },
      {
        field: "flightNumber",
        type: "string",
        pattern: /^\d{1,4}[A-Z]?$/,
        required: true,
      },
      {
        field: "date",
        type: "string",
        pattern: /^\d{4}-\d{2}-\d{2}$/,
        required: true,
      },
    ];

    expect(
      securityUtils.validateUserInput(validInput, validationRules).valid
    ).toBe(true);
    expect(
      securityUtils.validateUserInput(invalidInput, validationRules).valid
    ).toBe(false);
  });
});
```

### Integration Tests

Test automated workflows for the following scenarios:

1. **Flight Status Checking**:

   - Test with known flights across major airlines
   - Verify status parsing accuracy
   - Validate screenshot captures

2. **Check-in Automation**:

   - Test with mock confirmation codes
   - Verify error detection for invalid inputs
   - Confirm boarding pass detection

3. **Booking Verification**:
   - Test across flight, hotel, and car rental providers
   - Verify detail extraction accuracy
   - Confirm error handling

### End-to-End Testing

Create a verification script that tests the complete workflow:

```javascript
// test/e2e/browser-automation-e2e.js
const request = require("supertest");
const app = require("../../src/app");

describe("Browser Automation E2E Tests", () => {
  // Test flight status API
  test("GET /api/automation/flight-status returns correct status", async () => {
    const response = await request(app)
      .get("/api/automation/flight-status")
      .query({
        airline: "AA",
        flightNumber: "123",
        date: "2023-05-15",
      });

    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty("success");
    // More assertions based on expected response
  });

  // Test check-in API
  test("POST /api/automation/check-in performs check-in", async () => {
    const response = await request(app).post("/api/automation/check-in").send({
      airline: "AA",
      confirmationCode: "ABC123",
      lastName: "Smith",
      firstName: "John",
      flightDate: "2023-05-15",
    });

    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty("success");
    // More assertions based on expected response
  });

  // Test usage API
  test("GET /api/automation/usage returns usage statistics", async () => {
    const response = await request(app).get("/api/automation/usage");

    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty("minutesUsed");
    expect(response.body).toHaveProperty("minutesRemaining");
    // More assertions based on expected response
  });
});
```

## Advanced Features

### Browser Automation Agent

For more complex travel tasks, implement a dedicated automation agent:

```javascript
// src/agents/browser-automation-agent.js
class BrowserAutomationAgent {
  constructor(browserService) {
    this.browserService = browserService;
  }

  /**
   * Generate complete travel itinerary with screenshots
   * @param {Array} bookings List of bookings to include
   * @returns {Promise<Object>} Compiled itinerary
   */
  async generateTravelItinerary(bookings) {
    const itinerary = {
      title: "Your Travel Itinerary",
      created: new Date().toISOString(),
      bookings: [],
      screenshots: {},
    };

    for (const booking of bookings) {
      // Verify the booking
      const verificationResult = await this.browserService.verifyBooking(
        booking
      );

      if (verificationResult.success) {
        // Add to itinerary
        itinerary.bookings.push({
          type: booking.type,
          provider: booking.provider,
          confirmation: booking.confirmationCode,
          details: verificationResult.details,
        });

        // Store screenshot
        itinerary.screenshots[booking.confirmationCode] =
          verificationResult.screenshot;
      }
    }

    // Sort bookings by date
    itinerary.bookings.sort((a, b) => {
      const dateA = new Date(a.details.startDate || a.details.departureDate);
      const dateB = new Date(b.details.startDate || b.details.departureDate);
      return dateA - dateB;
    });

    return itinerary;
  }

  /**
   * Set up price monitoring for multiple travel items
   * @param {Array} items Travel items to monitor
   * @param {number} threshold Price change threshold percentage
   * @returns {Promise<Object>} Monitoring setup result
   */
  async setupPriceMonitoring(items, threshold = 5) {
    const monitoringResults = {
      setup: new Date().toISOString(),
      items: [],
      threshold: threshold,
    };

    for (const item of items) {
      // Check current price
      const priceResult = await this.browserService.monitorPrice(item);

      if (priceResult.success) {
        // Store initial price info
        monitoringResults.items.push({
          id: `${item.type}-${item.provider}-${item.destination}`,
          type: item.type,
          provider: item.provider,
          destination: item.destination,
          initialPrice: this.extractLowestPrice(priceResult.prices),
          lastChecked: new Date().toISOString(),
          screenshot: priceResult.screenshot,
        });
      }
    }

    return monitoringResults;
  }

  /**
   * Extract lowest price from price information
   * @private
   */
  extractLowestPrice(prices) {
    if (!prices || !prices.length) {
      return null;
    }

    const allPrices = prices
      .map((p) => parseFloat(p.amount.replace(/[^0-9.]/g, "")))
      .filter((p) => !isNaN(p));

    return allPrices.length > 0 ? Math.min(...allPrices) : null;
  }
}

module.exports = BrowserAutomationAgent;
```

## Troubleshooting

### Common Issues

1. **Element Not Found Errors**:

   - The website structure may have changed, requiring updated selectors
   - The element may be in an iframe or dynamically loaded
   - Solution: Use more robust element finding strategies, increase timeouts

2. **Authentication Challenges**:

   - Many travel sites use advanced bot detection
   - Solution: Use realistic user agent strings, enable cookies, handle captchas

3. **Varying Website Layouts**:

   - Travel sites often have different layouts for different regions
   - Solution: Implement adaptive form detection and filling

4. **Usage Limits Reached**:
   - You've hit the 100 minute monthly limit
   - Solution: Implement fallback strategies and strict prioritization

### Troubleshooting Steps

1. **Screenshot Analysis**:

   - Always capture screenshots at failure points
   - Compare with previous successful runs

2. **Console Log Collection**:

   - Gather browser console logs for JavaScript errors
   - Use browser_get_console_logs to retrieve logs

3. **Gradual Debugging**:

   - Break automation into smaller steps
   - Test each step individually

4. **Adaptive Retry**:
   - Implement exponential backoff for retries
   - Use alternative selectors as fallbacks

## Conclusion

The Browser-use integration enables TripSage to automate tedious travel tasks, enhancing the user experience significantly. By following the guidelines for cost optimization, security, and efficient implementation, you can provide a robust browser automation solution that works within the constraints of personal API key usage.

The integration covers:

- Flight status checking
- Booking verification
- Check-in automation
- Price monitoring
- Usage tracking and optimization

This implementation aligns with TripSage's overall integration strategy by providing value-added automation capabilities while respecting usage limitations and security best practices.

## Implementation Checklist

- [ ] Set up Browser-use account and obtain API key
- [ ] Configure environment variables
- [ ] Implement BrowserService class
- [ ] Create utility functions for automation
- [ ] Add security utilities
- [ ] Implement API routes
- [ ] Set up usage tracking
- [ ] Write tests
- [ ] Create documentation
- [ ] Implement advanced features (optional)
