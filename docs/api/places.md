# Places & Geolocation

Activities, places search, photos, and geolocation services.

## Activities

### `POST /api/activities/search`

Search for activities using Google Places Text Search.

**Authentication**: Anonymous  
**Rate Limit Key**: `activities:search`

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `textQuery` | string | Yes | Search query (min 1 char) |
| `maxResultCount` | number | No | Maximum results (default: 20, max: 20) |
| `locationBias` | object | No | Location bias object |
| `locationBias.lat` | number | No | Latitude |
| `locationBias.lon` | number | No | Longitude |
| `locationBias.radiusMeters` | number | No | Radius in meters |

#### Response

`200 OK`

```json
[
  {
    "id": "places/ChIJN1t_tDeuEmsRUsoyG83frY4",
    "displayName": "Louvre Museum",
    "formattedAddress": "Rue de Rivoli, 75001 Paris, France",
    "location": {
      "latitude": 48.8606,
      "longitude": 2.3376
    },
    "rating": 4.7,
    "userRatingCount": 123456,
    "photos": [
      {
        "name": "places/photo-reference"
      }
    ]
  }
]
```

#### Errors

- `400` - Invalid request parameters
- `429` - Rate limit exceeded

#### Example

```bash
curl -X POST "http://localhost:3000/api/activities/search" \
  -H "Content-Type: application/json" \
  -d '{
    "textQuery": "museum near Paris",
    "maxResultCount": 5
  }'
```

---

### `GET /api/activities/{id}`

Get activity/place details by Place ID.

**Authentication**: Anonymous  
**Rate Limit Key**: `activities:details`

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Google Place ID |

#### Response

`200 OK`

```json
{
  "id": "places/ChIJN1t_tDeuEmsRUsoyG83frY4",
  "displayName": "Louvre Museum",
  "formattedAddress": "Rue de Rivoli, 75001 Paris, France",
  "location": {
    "latitude": 48.8606,
    "longitude": 2.3376
  },
  "rating": 4.7,
  "userRatingCount": 123456,
  "photos": [
    {
      "name": "places/photo-reference"
    }
  ]
}
```

#### Errors

- `404` - Place not found
- `429` - Rate limit exceeded

---

## Places

### `POST /api/places/search`

Search for places using Google Places Text Search.

**Authentication**: Anonymous  
**Rate Limit Key**: `places:search`

#### Request Body

Identical to `POST /api/activities/search` - see Activities section above for complete schema details.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `textQuery` | string | Yes | Search query (min 1 char) |
| `maxResultCount` | number | No | Maximum results (default: 20, max: 20) |
| `locationBias` | object | No | Location bias {lat, lon, radiusMeters} |

#### Response

`200 OK`

```json
{
  "places": [
    {
      "id": "places/ChIJN1t_tDeuEmsRUsoyG83frY4",
      "displayName": {
        "text": "Louvre Museum",
        "languageCode": "en"
      },
      "formattedAddress": "Rue de Rivoli, 75001 Paris, France",
      "location": {
        "latitude": 48.8606,
        "longitude": 2.3376
      },
      "rating": 4.7,
      "userRatingCount": 123456,
      "photos": [
        {
          "name": "places/ChIJN1t_tDeuEmsRUsoyG83frY4/photos/AW30PQh8j1lbMpA1y2j6Cmbt1wEi4hlOnwRxfv-iEkT8ctM1wENl5A"
        }
      ],
      "types": ["museum", "tourist_attraction", "point_of_interest", "establishment"]
    }
  ]
}
```

#### Errors

- `400` - Invalid request parameters
- `429` - Rate limit exceeded

#### Example

```bash
curl -X POST "http://localhost:3000/api/places/search" \
  -H "Content-Type: application/json" \
  -d '{
    "textQuery": "museum in Paris",
    "maxResultCount": 5,
    "locationBias": {
      "lat": 48.8566,
      "lon": 2.3522,
      "radiusMeters": 10000
    }
  }'
```

---

### `GET /api/places/details/{id}`

Get place details by Place ID.

**Authentication**: Anonymous  
**Rate Limit Key**: `places:details`

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Google Place ID (with or without `places/` prefix) |

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sessionToken` | string | No | Session token for autocomplete |

#### Response

`200 OK`

```json
{
  "id": "places/ChIJN1t_tDeuEmsRUsoyG83frY4",
  "displayName": {
    "text": "Louvre Museum",
    "languageCode": "en"
  },
  "formattedAddress": "Rue de Rivoli, 75001 Paris, France",
  "location": {
    "latitude": 48.8606,
    "longitude": 2.3376
  },
  "url": "https://maps.google.com/?cid=10281119596374313554",
  "internationalPhoneNumber": "+33 1 40 20 50 50",
  "rating": 4.7,
  "userRatingCount": 123456,
  "regularOpeningHours": {
    "openNow": true,
    "weekdayDescriptions": [
      "Monday: Closed",
      "Tuesday: 9:00 AM – 6:00 PM",
      "Wednesday: 9:00 AM – 9:45 PM",
      "Thursday: 9:00 AM – 6:00 PM",
      "Friday: 9:00 AM – 9:45 PM",
      "Saturday: 9:00 AM – 6:00 PM",
      "Sunday: 9:00 AM – 6:00 PM"
    ]
  },
  "photos": [
    {
      "name": "places/ChIJN1t_tDeuEmsRUsoyG83frY4/photos/AW30PQh8j1lbMpA1y2j6Cmbt1wEi4hlOnwRxfv-iEkT8ctM1wENl5A"
    }
  ],
  "businessStatus": "OPERATIONAL",
  "types": ["museum", "tourist_attraction", "point_of_interest", "establishment"],
  "editorialSummary": {
    "text": "The Louvre, or the Louvre Museum, is a national art museum in Paris, France.",
    "languageCode": "en"
  }
}
```

#### Errors

- `404` - Place not found
- `429` - Rate limit exceeded

#### Example

```bash
curl "http://localhost:3000/api/places/details/ChIJN1t_tDeuEmsRUsoyG83frY4"
```

---

### `GET /api/places/photo`

Get place photo by photo reference name.

**Authentication**: Anonymous  
**Rate Limit Key**: `places:photo`

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Photo reference name |
| `maxWidthPx` | number | No | Maximum width in pixels |
| `maxHeightPx` | number | No | Maximum height in pixels |
| `skipHttpRedirect` | boolean | No | Skip HTTP redirect |

#### Response

`200 OK`

Returns binary image data (JPEG/PNG) with `Content-Type: image/jpeg` or `image/png` header.

**Note**: This endpoint returns binary image data, not JSON. The response body contains the raw image bytes.

#### Errors

- `400` - Missing photo reference
- `404` - Photo not found
- `429` - Rate limit exceeded

---

## Geolocation

### `POST /api/geocode`

Geocode an address or reverse geocode coordinates.

**Authentication**: Required  
**Rate Limit Key**: `geocode`

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `address` | string | No | Address to geocode |
| `lat` | number | No | Latitude (for reverse geocoding) |
| `lng` | number | No | Longitude (for reverse geocoding) |

#### Response

`200 OK` - Returns geocoding results

#### Errors

- `400` - Invalid request (must provide address OR lat/lng)
- `401` - Not authenticated
- `429` - Rate limit exceeded

#### Example

```bash
# Geocode an address
curl -X POST "http://localhost:3000/api/geocode" \
  --cookie "sb-access-token=$JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "address": "1 Rue de la Paix, 75002 Paris, France"
  }'

# Reverse geocode coordinates
curl -X POST "http://localhost:3000/api/geocode" \
  --cookie "sb-access-token=$JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 48.8606,
    "lng": 2.3376
  }'
```

---

### `POST /api/timezone`

Get timezone for coordinates.

**Authentication**: Required  
**Rate Limit Key**: `timezone`

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `lat` | number | Yes | Latitude |
| `lng` | number | Yes | Longitude |
| `timestamp` | number | No | Unix timestamp |

#### Response

`200 OK` - Returns timezone information

#### Errors

- `400` - Invalid coordinates
- `401` - Not authenticated
- `429` - Rate limit exceeded

#### Example

```bash
curl -X POST "http://localhost:3000/api/timezone" \
  --cookie "sb-access-token=$JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 48.8606,
    "lng": 2.3376
  }'
```

---

## Routes

### `POST /api/route-matrix`

Get distance/duration matrix for multiple origins and destinations.

**Authentication**: Required  
**Rate Limit Key**: `route-matrix`

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `origins` | array | Yes | Array of origin waypoints |
| `destinations` | array | Yes | Array of destination waypoints |
| `travelMode` | string | No | Travel mode (`DRIVE`, `WALK`, `BICYCLE`, `TRANSIT`) |

#### Response

`200 OK`

```json
[
  {
    "originIndex": 0,
    "destinationIndex": 0,
    "duration": "900s",
    "distanceMeters": 5230,
    "status": {
      "code": 0
    },
    "condition": "ROUTE_EXISTS"
  },
  {
    "originIndex": 0,
    "destinationIndex": 1,
    "duration": "1320s",
    "distanceMeters": 8740,
    "status": {
      "code": 0
    },
    "condition": "ROUTE_EXISTS"
  }
]
```

#### Errors

- `400` - Invalid request parameters
- `401` - Not authenticated
- `429` - Rate limit exceeded

---

### `POST /api/routes`

Multimodal route planner.

**Authentication**: Required  
**Rate Limit Key**: `routes`

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `origin` | object | Yes | Origin location |
| `destination` | object | Yes | Destination location |
| `travelMode` | string | No | Travel mode |
| `routingPreference` | string | No | Routing preference (`TRAFFIC_AWARE`, `TRAFFIC_UNAWARE`) |

#### Response

`200 OK`

```json
{
  "routes": [
    {
      "duration": "900s",
      "distanceMeters": 5230,
      "polyline": {
        "encodedPolyline": "u{~|Fnyys@fS_DzBmO"
      },
      "legs": [
        {
          "stepCount": 12
        }
      ],
      "routeLabels": ["DEFAULT_ROUTE"]
    }
  ]
}
```

#### Errors

- `400` - Invalid request parameters
- `401` - Not authenticated
- `429` - Rate limit exceeded
