// Polyline - decode the Google encoded polyline (precision 5) that OSRM returns

export type LatLng = [number, number];

export function decodePolyline(encoded: string): LatLng[] {
  const points: LatLng[] = [];
  let index = 0;
  let lat = 0;
  let lng = 0;
  while (index < encoded.length) {
    const deltas: number[] = [];
    for (let part = 0; part < 2; part += 1) {
      let shift = 0;
      let result = 0;
      let byte: number;
      do {
        byte = encoded.charCodeAt(index) - 63;
        index += 1;
        result |= (byte & 0x1f) << shift;
        shift += 5;
      } while (byte >= 0x20);
      deltas.push(result & 1 ? ~(result >> 1) : result >> 1);
    }
    lat += deltas[0];
    lng += deltas[1];
    points.push([lat / 1e5, lng / 1e5]);
  }
  return points;
}

/** Road geometry when OSRM answered, else straight segments between the points. */
export function routeLine(geometry: string | null | undefined, fallback: LatLng[]): LatLng[] {
  return geometry ? decodePolyline(geometry) : fallback;
}
