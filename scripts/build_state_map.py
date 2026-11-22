"""Build frontend/src/state-map.json from INEGI's Marco Geoestadístico (state level).

Downloads https://gaia.inegi.org.mx/wscatgeo/v2/geo/mgee/ (no token), projects it with the Lambert conformal conic
parameters INEGI uses for Mexico, simplifies the outlines (Ramer-Douglas-Peucker) and stores one SVG path per state.
Standard library only. Run:  python3 scripts/build_state_map.py [--input mgee.json]
"""
from __future__ import annotations

import argparse
import json
import math
import urllib.request
from pathlib import Path

URL = "https://gaia.inegi.org.mx/wscatgeo/v2/geo/mgee/"
OUT = Path(__file__).resolve().parents[1] / "frontend" / "src" / "state-map.json"
WIDTH = 1000          # drawing units across the widest side
TOLERANCE = 0.9       # simplification tolerance in drawing units
MIN_RING_AREA = 1.2   # drop islands smaller than this (drawing units squared) unless they are the state's largest ring

PHI1, PHI2, PHI0, LAM0 = map(math.radians, (17.5, 29.5, 12.0, -102.0))
_N = math.log(math.cos(PHI1) / math.cos(PHI2)) / math.log(math.tan(math.pi / 4 + PHI2 / 2) / math.tan(math.pi / 4 + PHI1 / 2))
_F = math.cos(PHI1) * math.tan(math.pi / 4 + PHI1 / 2) ** _N / _N
_RHO0 = _F / math.tan(math.pi / 4 + PHI0 / 2) ** _N


def project(lon: float, lat: float) -> tuple[float, float]:
    rho = _F / math.tan(math.pi / 4 + math.radians(lat) / 2) ** _N
    theta = _N * (math.radians(lon) - LAM0)
    return rho * math.sin(theta), _RHO0 - rho * math.cos(theta)


def rdp(points: list[tuple[float, float]], tolerance: float) -> list[tuple[float, float]]:
    if len(points) < 3:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        start, end = stack.pop()
        (x1, y1), (x2, y2) = points[start], points[end]
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        far, far_distance = -1, 0.0
        for index in range(start + 1, end):
            x, y = points[index]
            distance = abs(dy * (x - x1) - dx * (y - y1)) / length if length else math.hypot(x - x1, y - y1)
            if distance > far_distance:
                far, far_distance = index, distance
        if far_distance > tolerance:
            keep[far] = True
            stack += [(start, far), (far, end)]
    return [point for point, kept in zip(points, keep) if kept]


def ring_area(ring: list[tuple[float, float]]) -> float:
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]))) / 2


def load(path: str | None) -> dict:
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    with urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "arancel-mx-build"}), timeout=120) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="a previously downloaded mgee.json")
    raw = load(parser.parse_args().input)
    states = []
    for feature in raw["features"]:
        geometry = feature["geometry"]
        polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
        states.append((feature["properties"], [[[project(lon, lat) for lon, lat in ring] for ring in polygon] for polygon in polygons]))
    xs = [x for _, polygons in states for polygon in polygons for ring in polygon for x, _ in ring]
    ys = [y for _, polygons in states for polygon in polygons for ring in polygon for _, y in ring]
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    scale = WIDTH / (max_x - min_x)
    height = round((max_y - min_y) * scale)

    def to_view(point: tuple[float, float]) -> tuple[float, float]:
        return (point[0] - min_x) * scale, (max_y - point[1]) * scale

    out = []
    for properties, polygons in states:
        rings = [[to_view(point) for point in polygon[0]] for polygon in polygons]  # outer rings only: holes are not visible here
        simplified = [(ring_area(ring), rdp(ring, TOLERANCE)) for ring in rings]
        largest = max(area for area, _ in simplified)
        parts = []
        for area, ring in simplified:
            if (area >= MIN_RING_AREA or area == largest) and len(ring) >= 4:
                parts.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in ring[:-1]) + "Z")
        out.append({"cve_ent": properties["cve_ent"], "name": properties["nomgeo"], "population": int(float(properties["pob_total"])), "d": "".join(parts)})
    bundle = {
        "source": raw.get("metadatos", {}).get("Fuente_informacion_vectorial", "INEGI. Marco Geoestadístico"),
        "population_source": raw.get("metadatos", {}).get("Fuente_informacion_estadistica", "INEGI. Censo de Población y Vivienda, 2020"),
        "service": URL,
        "projection": "Cónica conforme de Lambert (paralelos 17.5 y 29.5, origen 12 N, 102 O), contornos simplificados",
        "width": WIDTH,
        "height": height,
        "states": sorted(out, key=lambda item: item["cve_ent"]),
    }
    OUT.write_text(json.dumps(bundle, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(out)} states, {OUT.stat().st_size / 1024:.0f} KB, viewBox 0 0 {WIDTH} {height}")


if __name__ == "__main__":
    main()
