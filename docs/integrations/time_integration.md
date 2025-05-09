# Time MCP Server Integration

This document outlines the implementation details for the Time MCP Server, which provides timezone conversion and time management capabilities for the TripSage travel planning system.

## Overview

The Time MCP Server provides essential time-related functionality for the TripSage application, including timezone conversion, date manipulation, and scheduling utilities. These capabilities are critical for a travel planning system that must coordinate activities across multiple timezones, manage flight arrival and departure times, and create accurate itineraries with proper local time information.

## Technology Selection

After evaluating multiple time management libraries and implementation approaches, we selected the following technology stack:

- **Node.js**: JavaScript runtime for the server implementation
- **TypeScript**: Type-safe language for robust code quality
- **Luxon**: Comprehensive datetime library for timezone handling and calculations
- **FastMCP**: High-level framework for building MCP servers with minimal boilerplate
- **Docker**: For containerized deployment

Luxon was chosen over other datetime libraries (like Moment.js, date-fns, or Day.js) for the following reasons:

- Immutable API that prevents unintended modifications
- Comprehensive timezone support using the IANA timezone database
- Proper handling of DST (Daylight Saving Time) transitions
- Support for date/time arithmetic with units (e.g., adding days, hours)
- Robust parsing and formatting capabilities
- Active maintenance and modern design

## MCP Tools

The Time MCP Server exposes the following key tools:

### get_current_time

Retrieves the current time in a specific timezone.

```typescript
@mcp.tool()
async function get_current_time(
  { timezone }: { timezone: string }
): Promise<CurrentTimeResult> {
  try {
    // Validate timezone
    if (!isValidTimezone(timezone)) {
      throw new Error(`Invalid timezone: ${timezone}`);
    }

    // Get current time in the specified timezone
    const now = DateTime.now().setZone(timezone);

    return {
      timezone: timezone,
      iso8601: now.toISO(),
      utc_offset: now.offset / 60, // Convert minutes to hours
      formatted: {
        full: now.toFormat('EEEE, MMMM d, yyyy h:mm a'),
        date: now.toFormat('yyyy-MM-dd'),
        time: now.toFormat('HH:mm:ss'),
        time_12h: now.toFormat('h:mm a'),
        time_24h: now.toFormat('HH:mm'),
        timezone_name: now.zoneName,
        timezone_abbreviation: now.toFormat('ZZZZ')
      },
      timezone_info: {
        name: now.zoneName,
        country_code: getTimezoneCountryCode(timezone),
        dst_active: now.isInDST
      }
    };
  } catch (error) {
    throw new Error(`Error getting current time: ${error.message}`);
  }
}
```

### convert_time

Converts a time from one timezone to another.

```typescript
@mcp.tool()
async function convert_time(
  {
    time,
    source_timezone,
    target_timezone,
    format
  }: {
    time: string,
    source_timezone: string,
    target_timezone: string,
    format?: string
  }
): Promise<TimeConversionResult> {
  try {
    // Validate timezones
    if (!isValidTimezone(source_timezone)) {
      throw new Error(`Invalid source timezone: ${source_timezone}`);
    }

    if (!isValidTimezone(target_timezone)) {
      throw new Error(`Invalid target timezone: ${target_timezone}`);
    }

    // Parse input time
    let dateTime: DateTime;
    if (time === 'now') {
      dateTime = DateTime.now().setZone(source_timezone);
    } else {
      // Try different input formats
      const formats = [
        'yyyy-MM-dd HH:mm:ss',
        'yyyy-MM-dd HH:mm',
        'yyyy-MM-dd',
        'HH:mm:ss',
        'HH:mm',
        'h:mm a'
      ];

      let parsed = false;
      for (const fmt of formats) {
        const attempt = DateTime.fromFormat(time, fmt, { zone: source_timezone });
        if (attempt.isValid) {
          dateTime = attempt;
          parsed = true;
          break;
        }
      }

      if (!parsed) {
        // Try ISO format
        dateTime = DateTime.fromISO(time, { zone: source_timezone });

        if (!dateTime.isValid) {
          throw new Error(`Could not parse time: ${time}`);
        }
      }
    }

    // Convert to target timezone
    const convertedTime = dateTime.setZone(target_timezone);

    // Format the output
    const outputFormat = format || 'yyyy-MM-dd HH:mm:ss';

    return {
      original: {
        time: dateTime.toFormat(outputFormat),
        timezone: source_timezone,
        utc_offset: dateTime.offset / 60
      },
      converted: {
        time: convertedTime.toFormat(outputFormat),
        timezone: target_timezone,
        utc_offset: convertedTime.offset / 60
      },
      difference_hours: (convertedTime.offset - dateTime.offset) / 60,
      iso8601: convertedTime.toISO()
    };
  } catch (error) {
    throw new Error(`Error converting time: ${error.message}`);
  }
}
```

### calculate_travel_time

Calculates arrival time and total duration for travel between timezones.

```typescript
@mcp.tool()
async function calculate_travel_time(
  {
    departure_time,
    departure_timezone,
    duration_hours,
    arrival_timezone
  }: {
    departure_time: string,
    departure_timezone: string,
    duration_hours: number,
    arrival_timezone: string
  }
): Promise<TravelTimeResult> {
  try {
    // Validate timezones
    if (!isValidTimezone(departure_timezone)) {
      throw new Error(`Invalid departure timezone: ${departure_timezone}`);
    }

    if (!isValidTimezone(arrival_timezone)) {
      throw new Error(`Invalid arrival timezone: ${arrival_timezone}`);
    }

    // Parse departure time
    let departureDateTime: DateTime;
    if (departure_time === 'now') {
      departureDateTime = DateTime.now().setZone(departure_timezone);
    } else {
      // Try different input formats
      const formats = [
        'yyyy-MM-dd HH:mm:ss',
        'yyyy-MM-dd HH:mm',
        'yyyy-MM-dd',
        'HH:mm:ss',
        'HH:mm',
        'h:mm a'
      ];

      let parsed = false;
      for (const fmt of formats) {
        const attempt = DateTime.fromFormat(departure_time, fmt, { zone: departure_timezone });
        if (attempt.isValid) {
          departureDateTime = attempt;
          parsed = true;
          break;
        }
      }

      if (!parsed) {
        // Try ISO format
        departureDateTime = DateTime.fromISO(departure_time, { zone: departure_timezone });

        if (!departureDateTime.isValid) {
          throw new Error(`Could not parse departure time: ${departure_time}`);
        }
      }
    }

    // Calculate arrival time
    const durationInMillis = duration_hours * 60 * 60 * 1000;
    const arrivalDateTimeLocal = departureDateTime.plus({ milliseconds: durationInMillis });
    const arrivalDateTimeDestination = arrivalDateTimeLocal.setZone(arrival_timezone);

    // Calculate time difference between departure and arrival timezones
    const departureTZ = DateTime.now().setZone(departure_timezone);
    const arrivalTZ = DateTime.now().setZone(arrival_timezone);
    const tzDifferenceHours = (arrivalTZ.offset - departureTZ.offset) / 60;

    return {
      departure: {
        time: departureDateTime.toFormat('yyyy-MM-dd HH:mm'),
        timezone: departure_timezone,
        utc_offset: departureDateTime.offset / 60
      },
      arrival: {
        time: arrivalDateTimeDestination.toFormat('yyyy-MM-dd HH:mm'),
        timezone: arrival_timezone,
        utc_offset: arrivalDateTimeDestination.offset / 60
      },
      flight_duration_hours: duration_hours,
      timezone_difference_hours: tzDifferenceHours,
      local_time_difference_hours: duration_hours + tzDifferenceHours,
      next_day_arrival: arrivalDateTimeDestination.day > departureDateTime.day ||
                          arrivalDateTimeDestination.month > departureDateTime.month ||
                          arrivalDateTimeDestination.year > departureDateTime.year,
      previous_day_arrival: arrivalDateTimeDestination.day < departureDateTime.day &&
                            !(arrivalDateTimeDestination.month > departureDateTime.month ||
                              arrivalDateTimeDestination.year > departureDateTime.year)
    };
  } catch (error) {
    throw new Error(`Error calculating travel time: ${error.message}`);
  }
}
```

### list_timezones

Retrieves a list of all valid IANA timezones, optionally filtered by region or query.

```typescript
@mcp.tool()
async function list_timezones(
  {
    region,
    query
  }: {
    region?: string,
    query?: string
  }
): Promise<TimezoneListResult> {
  try {
    // Get all IANA timezones
    const allTimezones = getIANATimezones();

    // Filter by region if specified
    let filteredTimezones = allTimezones;
    if (region) {
      const normalizedRegion = region.toLowerCase();
      filteredTimezones = allTimezones.filter(tz =>
        tz.toLowerCase().startsWith(normalizedRegion + '/') ||
        tz.toLowerCase() === normalizedRegion
      );
    }

    // Filter by query if specified
    if (query) {
      const normalizedQuery = query.toLowerCase();
      filteredTimezones = filteredTimezones.filter(tz =>
        tz.toLowerCase().includes(normalizedQuery)
      );
    }

    // Get current time for each timezone
    const timezones = filteredTimezones.map(tz => {
      const now = DateTime.now().setZone(tz);
      return {
        name: tz,
        utc_offset: now.offset / 60,
        utc_offset_formatted: now.toFormat('Z'),
        current_time: now.toFormat('HH:mm'),
        region: tz.split('/')[0],
        location: tz.includes('/') ? tz.split('/').slice(1).join('/') : tz,
        dst_active: now.isInDST
      };
    });

    // Sort by UTC offset
    timezones.sort((a, b) => a.utc_offset - b.utc_offset);

    return {
      count: timezones.length,
      timezones: timezones
    };
  } catch (error) {
    throw new Error(`Error listing timezones: ${error.message}`);
  }
}
```

### format_date

Formats a date according to specified format and locale.

```typescript
@mcp.tool()
async function format_date(
  {
    date,
    format,
    timezone,
    locale
  }: {
    date: string,
    format: string,
    timezone?: string,
    locale?: string
  }
): Promise<DateFormatResult> {
  try {
    // Set timezone
    const tz = timezone && isValidTimezone(timezone) ? timezone : 'UTC';

    // Set locale
    const loc = locale || 'en-US';

    // Parse date
    let dateTime: DateTime;
    if (date === 'now') {
      dateTime = DateTime.now().setZone(tz);
    } else {
      // Try different input formats
      const formats = [
        'yyyy-MM-dd HH:mm:ss',
        'yyyy-MM-dd HH:mm',
        'yyyy-MM-dd',
        'MM/dd/yyyy',
        'dd/MM/yyyy'
      ];

      let parsed = false;
      for (const fmt of formats) {
        const attempt = DateTime.fromFormat(date, fmt, { zone: tz });
        if (attempt.isValid) {
          dateTime = attempt;
          parsed = true;
          break;
        }
      }

      if (!parsed) {
        // Try ISO format
        dateTime = DateTime.fromISO(date, { zone: tz });

        if (!dateTime.isValid) {
          throw new Error(`Could not parse date: ${date}`);
        }
      }
    }

    // Format date
    return {
      formatted: dateTime.setLocale(loc).toFormat(format),
      timezone: tz,
      locale: loc,
      iso8601: dateTime.toISO()
    };
  } catch (error) {
    throw new Error(`Error formatting date: ${error.message}`);
  }
}
```

## Implementation Details

### Server Architecture

The Time MCP Server follows a clean architecture with separation of concerns:

1. **Core**: MCP server setup and configuration
2. **Utils**: Helper functions for timezone validation and manipulation
3. **Models**: Type definitions and interfaces
4. **Tools**: MCP tool implementations

### Key Components

#### Server Entry Point

```typescript
// index.ts
import { FastMCP } from "fastmcp";
import {
  get_current_time,
  convert_time,
  calculate_travel_time,
  list_timezones,
  format_date,
} from "./tools";

// Create MCP server
const server = new FastMCP({
  name: "time-mcp",
  version: "1.0.0",
  description: "Time MCP Server for TripSage",
});

// Register tools
server.registerTool(get_current_time);
server.registerTool(convert_time);
server.registerTool(calculate_travel_time);
server.registerTool(list_timezones);
server.registerTool(format_date);

// Start the server
const port = parseInt(process.env.PORT || "3000");
server.start({
  transportType: process.env.TRANSPORT_TYPE || "stdio",
  http: {
    port: port,
  },
});

console.log(`Time MCP Server started`);
```

#### Timezone Utilities

```typescript
// utils/timezone.ts
import { DateTime } from "luxon";
import tzdata from "tzdata";

// Cache for timezone validity
const validTimezoneCache = new Map<string, boolean>();

/**
 * Checks if a timezone is valid
 */
export function isValidTimezone(timezone: string): boolean {
  // Check cache first
  if (validTimezoneCache.has(timezone)) {
    return validTimezoneCache.get(timezone)!;
  }

  // Validate timezone
  try {
    const dt = DateTime.now().setZone(timezone);
    const isValid = dt.isValid;

    // Cache result
    validTimezoneCache.set(timezone, isValid);

    return isValid;
  } catch (error) {
    validTimezoneCache.set(timezone, false);
    return false;
  }
}

/**
 * Returns the country code for a timezone
 */
export function getTimezoneCountryCode(timezone: string): string | null {
  const tzInfo = tzdata[timezone];
  return tzInfo?.countries?.[0] || null;
}

/**
 * Returns all IANA timezones
 */
export function getIANATimezones(): string[] {
  return Object.keys(tzdata);
}

/**
 * Get timezone abbreviation for a specific timezone and date
 */
export function getTimezoneAbbreviation(
  timezone: string,
  date?: string
): string {
  const dt = date
    ? DateTime.fromISO(date, { zone: timezone })
    : DateTime.now().setZone(timezone);

  return dt.toFormat("ZZZZ");
}
```

## Integration with TripSage

The Time MCP Server integrates with TripSage in the following ways:

### Agent Integration

The Travel Agent uses the Time MCP Server for several key functions in the travel planning process:

1. **Flight Time Calculations**: Convert flight departure and arrival times between timezones
2. **Itinerary Planning**: Display activities in the correct local time for each destination
3. **Booking Optimization**: Determine optimal booking times across different timezones
4. **Timezone Awareness**: Provide contextual timezone information to travelers
5. **Travel Duration Management**: Calculate total travel time including timezone changes

### Data Flow

1. **Input**: Travel agent receives time information such as departure times and flight durations
2. **Processing**: The agent uses the Time MCP Server to calculate local times and make conversions
3. **Integration**: Timezone-adjusted times are incorporated into the travel plan
4. **Storage**: Time information is stored with proper timezone context in Supabase
5. **Presentation**: Times are formatted consistently across the itinerary

### Example Use Cases

- **International Flight Planning**: Converting departure and arrival times between origin and destination timezones
- **Multi-City Itinerary**: Ensuring activities in different cities use the correct local time
- **Jet Lag Management**: Calculating optimal sleep and wake times based on timezone changes
- **Booking Windows**: Determining the best time to book activities based on local business hours
- **Conference Call Scheduling**: Coordinating virtual meetings across multiple timezones

## Deployment and Configuration

### Environment Variables

| Variable         | Description                                    | Default             |
| ---------------- | ---------------------------------------------- | ------------------- |
| PORT             | Port for the MCP server                        | 3000                |
| TRANSPORT_TYPE   | MCP transport type (stdio or http)             | stdio               |
| DEFAULT_TIMEZONE | Default timezone to use when none is specified | UTC                 |
| DEFAULT_LOCALE   | Default locale for date formatting             | en-US               |
| DEFAULT_FORMAT   | Default date format                            | yyyy-MM-dd HH:mm:ss |

### Deployment Options

1. **Docker Container**: The recommended deployment method

   ```bash
   docker build -t time-mcp .
   docker run time-mcp
   ```

2. **NPM Package**: For direct integration with other Node.js services

   ```bash
   npm install @tripsage/time-mcp-server
   npx @tripsage/time-mcp-server
   ```

3. **Local Development**: For testing and development
   ```bash
   npm install
   npm start
   ```

## Best Practices

1. **Timezone Names**: Always use IANA timezone names (e.g., "America/New_York") rather than abbreviations (e.g., "EST")
2. **Date Format**: Use ISO 8601 format (YYYY-MM-DD) for date interchange
3. **Time Zones vs. Offsets**: Store timezone names rather than offsets to handle DST changes
4. **Validation**: Validate timezone inputs to prevent errors
5. **Formatting**: Use locale-aware formatting for user-facing displays
6. **Error Handling**: Provide clear error messages for invalid inputs
7. **Caching**: Cache timezone data to improve performance

## Limitations and Future Enhancements

### Current Limitations

- No historical timezone data for dates before the IANA database
- Limited support for non-standard time formats
- No support for astronomical time calculations (sunrise/sunset)
- Limited calendar functionality

### Planned Enhancements

1. **Calendar Integration**: Add tools for creating and managing calendar events
2. **Working Hours**: Support for calculating business hours across timezones
3. **Sunrise/Sunset Calculations**: Add support for calculating dawn/dusk times for locations
4. **Historical Time Data**: Extend support for historical timezone changes
5. **Natural Language Processing**: Parse relative time expressions (e.g., "next Monday")
6. **Flight Schedule Integration**: Direct integration with flight APIs for accurate timezone handling

## Conclusion

The Time MCP Server provides essential timezone and time management capabilities for the TripSage travel planning system. By offering robust tools for timezone conversion, travel time calculation, and date formatting, it enables TripSage to provide accurate, timezone-aware travel plans. The implementation uses modern libraries and follows best practices for timezone handling, ensuring that travelers receive reliable time information regardless of their destination.

This integration is particularly critical for international travel planning, where accurate timezone information can significantly impact the travel experience. The Time MCP Server's capabilities will continue to be expanded to support more advanced time-related functionality, improving TripSage's ability to create comprehensive, timezone-aware travel plans.
