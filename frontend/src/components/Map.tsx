/**
 * @fileoverview Google Maps component with Advanced Markers.
 *
 * Client-side map component using Maps JavaScript API with Map ID, Advanced
 * Markers, and Places integration. Loads Maps JS via importLibrary.
 */

"use client";

import { useEffect, useRef, useState } from "react";

declare global {
  interface Window {
    google?: typeof google;
    initMap?: () => void;
  }
}

interface MapProps {
  center: { lat: number; lng: number };
  zoom?: number;
  mapId?: string;
  markers?: Array<{
    placeId?: string;
    lat: number;
    lng: number;
    title?: string;
    photoName?: string;
  }>;
  onMarkerClick?: (marker: {
    placeId?: string;
    lat: number;
    lng: number;
    title?: string;
  }) => void;
}

/**
 * Google Maps component with Advanced Markers.
 *
 * @param props Map configuration props.
 */
export function GoogleMap({
  center,
  zoom = 10,
  mapId,
  markers = [],
  onMarkerClick,
}: MapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const [_map, setMap] = useState<google.maps.Map | null>(null);
  const [_advancedMarkers, setAdvancedMarkers] = useState<
    google.maps.marker.AdvancedMarkerElement[]
  >([]);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    if (isLoaded || typeof window === "undefined") return;

    const apiKey =
      process.env.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY ||
      process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;

    if (!apiKey) {
      console.warn(
        "Google Maps browser API key not configured. Set NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY."
      );
      return;
    }

    // Load Maps JS API script if not already loaded
    if (window.google?.maps) {
      setIsLoaded(true);
    } else {
      const script = document.createElement("script");
      script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&loading=async&libraries=marker,places`;
      script.async = true;
      script.defer = true;
      script.onload = () => {
        setIsLoaded(true);
      };
      document.head.appendChild(script);
    }
  }, [isLoaded]);

  useEffect(() => {
    if (!isLoaded || !mapRef.current || !window.google?.maps) return;

    const initMap = async () => {
      const mapsLibrary = await window.google.maps.importLibrary("maps");
      // @ts-expect-error - Map may not be fully typed
      const GoogleMap = mapsLibrary.Map;
      const markerLibrary = await window.google.maps.importLibrary("marker");
      // @ts-expect-error - AdvancedMarkerElement and PinElement may not be fully typed
      const { AdvancedMarkerElement, PinElement } = markerLibrary;

      if (!mapRef.current) return;
      const mapInstance = new GoogleMap(mapRef.current, {
        center,
        disableDefaultUI: false,
        mapId: mapId ?? "DEMO_MAP_ID", // Replace with your Map ID
        zoom,
      });

      setMap(mapInstance);

      // Clear existing markers
      setAdvancedMarkers((prevMarkers) => {
        prevMarkers.forEach((marker) => {
          marker.map = null;
        });
        return [];
      });

      // Create Advanced Markers
      const newMarkers: google.maps.marker.AdvancedMarkerElement[] = [];

      for (const markerData of markers) {
        const pinElement = new PinElement({
          background: "#4285F4",
          borderColor: "#1976D2",
          glyphColor: "#FFFFFF",
          scale: 1.2,
        });

        const marker = new AdvancedMarkerElement({
          content: pinElement.element,
          map: mapInstance,
          position: { lat: markerData.lat, lng: markerData.lng },
          title: markerData.title,
        });

        if (onMarkerClick) {
          marker.addListener("click", () => {
            onMarkerClick({
              lat: markerData.lat,
              lng: markerData.lng,
              placeId: markerData.placeId,
              title: markerData.title,
            });
          });
        }

        newMarkers.push(marker);
      }

      setAdvancedMarkers(newMarkers);
    };

    initMap().catch(console.error);
  }, [isLoaded, center, zoom, mapId, markers, onMarkerClick]);

  return (
    <div ref={mapRef} style={{ height: "100%", minHeight: "400px", width: "100%" }} />
  );
}
