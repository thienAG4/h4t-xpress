// Geolocation helpers - one-shot browser position and straight-line distance

export type GeoPoint = { lat: number; lng: number; accuracy_m?: number };

/** Current position, or null when GPS is refused, unavailable or too slow. */
export function currentPosition(timeoutMs = 5_000): Promise<GeoPoint | null> {
  if (!("geolocation" in navigator)) return Promise.resolve(null);
  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      ({ coords }) =>
        resolve({ lat: coords.latitude, lng: coords.longitude, accuracy_m: Math.round(coords.accuracy) }),
      () => resolve(null),
      { enableHighAccuracy: true, timeout: timeoutMs, maximumAge: 10_000 },
    );
  });
}

export function distanceKm(a: { lat: number; lng: number }, b: { lat: number; lng: number }): number {
  const toRad = (degrees: number) => (degrees * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(h));
}
