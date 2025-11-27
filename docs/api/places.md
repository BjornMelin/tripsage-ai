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

`200 OK` - Returns place details object

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

Same as `POST /api/activities/search`

#### Response

`200 OK` - Returns places array

#### Errors

- `400` - Invalid request parameters
- `429` - Rate limit exceeded

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

`200 OK` - Returns place details with minimal field mask

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

`200 OK` - Returns photo image data

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

`200 OK` - Returns route matrix

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

`200 OK` - Returns route information

#### Errors

- `400` - Invalid request parameters
- `401` - Not authenticated
- `429` - Rate limit exceeded
