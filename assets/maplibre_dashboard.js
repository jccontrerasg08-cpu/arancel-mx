(function () {
  "use strict";

  const bridges = new Map();
  const EMPTY_COUNTRIES = Object.freeze({ type: "FeatureCollection", features: [] });
  const DARK_STYLE = {
    version: 8,
    sources: {
      carto: {
        type: "raster",
        tiles: [
          "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
          "https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
          "https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"
        ],
        tileSize: 256,
        attribution: "&copy; OpenStreetMap contributors &copy; CARTO"
      }
    },
    layers: [
      { id: "local-dark-bg", type: "background", paint: { "background-color": "#07120d" } },
      { id: "carto-dark", type: "raster", source: "carto", paint: { "raster-opacity": 0.72 } }
    ]
  };

  function parseConfig(el) {
    try {
      return JSON.parse(el.getAttribute("data-config") || "{}");
    } catch (_err) {
      return {};
    }
  }

  function setDashInput(id, payload) {
    const input = document.getElementById(id);
    if (!input) return;
    const value = JSON.stringify(Object.assign({ ts: Date.now() }, payload));
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
    setter.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function fmtNumber(value) {
    const n = Number(value || 0);
    return Math.round(n).toLocaleString("es-MX");
  }

  function fmtMoney(value, unit) {
    if (value === null || value === undefined || value === "") return "n.d.";
    return "$" + fmtNumber(value) + " " + unit;
  }

  function popupHtml(kind, props) {
    if (kind === "world") {
      const flag = props.flag_url
        ? "<img src=\"" + props.flag_url + "\" alt=\"Bandera " + props.name + "\" class=\"popup-flag\">"
        : "";
      return [
        "<div class=\"popup-country\">" + flag + "<strong>" + props.name + " (" + props.iso3 + ")</strong></div>",
        "Exportaciones nacionales: " + fmtMoney(props.national_exports, "MDD"),
        "Importaciones nacionales: " + fmtMoney(props.national_imports, "MDD"),
        "Balanza: " + fmtMoney(props.balance, "MDD"),
        "Periodo: " + (props.period || "n.d.")
      ].join("<br>");
    }
    return [
      "<strong>" + props.name + "</strong>",
      props.url ? "<a class=\"popup-link\" href=\"" + props.url + "\" target=\"_blank\" rel=\"noopener noreferrer\">Abrir ficha ANAM</a>" : "",
      props.tipo ? "Tipo: " + props.tipo : "",
      "Total: " + fmtMoney(props.total, "MDP"),
      "IVA: " + fmtMoney(props.iva, "MDP"),
      "IGI: " + fmtMoney(props.igi, "MDP"),
      "Var.: " + Number(props.variation || 0).toFixed(1) + "%"
    ].filter(Boolean).join("<br>");
  }

  function upsertSource(map, id, data) {
    const source = map.getSource(id);
    if (source) {
      source.setData(data);
    } else {
      map.addSource(id, { type: "geojson", data: data });
    }
  }

  function safeAddLayer(map, layer) {
    try {
      if (!map.getLayer(layer.id)) map.addLayer(layer);
    } catch (err) {
      console.warn("Map layer skipped:", layer.id, err);
    }
  }

  function featureMap(features) {
    const out = new Map();
    (features || []).forEach((feature) => out.set(String(feature.properties.id), feature.properties));
    return out;
  }

  function selectedFilter(selected) {
    return ["in", ["get", "id"], ["literal", Array.from(selected)]];
  }

  async function loadCountries() {
    return EMPTY_COUNTRIES;
  }

  class MapBridge {
    constructor(el) {
      this.el = el;
      this.id = el.id;
      this.config = parseConfig(el);
      this.kind = this.config.kind;
      this.selected = new Set();
      this.propsById = new Map();
      this.loaded = false;
      this.popup = null;
      this.countries = null;
      this.map = new maplibregl.Map({
        container: el,
        style: DARK_STYLE,
        center: this.config.center || [-102.5, 23.6],
        zoom: this.config.zoom || 3,
        attributionControl: false
      });
      this.map.addControl(new maplibregl.NavigationControl({ visualizePitch: false }), "top-right");
      this.map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");
      this.map.on("load", () => {
        this.loaded = true;
        loadCountries()
          .then((countries) => {
            this.countries = countries;
            this.draw();
          })
          .catch(() => this.draw());
      });
      this.map.on("error", () => {
        this.el.classList.add("maplibre-tile-fallback");
      });
    }

    updateFromDom() {
      this.config = parseConfig(this.el);
      this.kind = this.config.kind;
      if (this.loaded) this.draw();
    }

    draw() {
      if (this.kind === "world") this.drawWorld();
      if (this.kind === "customs") this.drawCustoms();
      this.map.resize();
    }

    ensureCountrySource() {
      if (this.map.getSource("country-polygons")) return true;
      if (!this.countries) return false;
      this.map.addSource("country-polygons", {
        type: "geojson",
        data: this.countries,
        promoteId: "id"
      });
      safeAddLayer(this.map, {
        id: "country-base-fill",
        type: "fill",
        source: "country-polygons",
        paint: {
          "fill-color": "#153326",
          "fill-opacity": 0.22
        }
      });
      safeAddLayer(this.map, {
        id: "country-base-outline",
        type: "line",
        source: "country-polygons",
        paint: {
          "line-color": "#6f9184",
          "line-width": 0.45,
          "line-opacity": 0.32
        }
      });
      return true;
    }

    drawWorld() {
      const points = this.config.points || { type: "FeatureCollection", features: [] };
      const arcs = this.config.arcs || { type: "FeatureCollection", features: [] };
      this.propsById = featureMap(points.features);
      this.selected = new Set(Array.from(this.selected).filter((id) => this.propsById.has(id)));

      this.ensureCountrySource();
      upsertSource(this.map, "world-points", points);
      upsertSource(this.map, "world-arcs", arcs);

      safeAddLayer(this.map, {
        id: "country-fill",
        type: "fill",
        source: "country-polygons",
        filter: ["in", ["get", "id"], ["literal", this.config.countryIds || []]],
        paint: {
          "fill-color": [
            "case",
            ["boolean", ["feature-state", "selected"], false], "#d8a93a",
            [">=", ["to-number", ["feature-state", "balance"], 0], 0], "#1f8a5b",
            "#8f2931"
          ],
          "fill-opacity": [
            "case",
            ["boolean", ["feature-state", "selected"], false], 0.62,
            0.28
          ]
        }
      });
      safeAddLayer(this.map, {
        id: "country-outline",
        type: "line",
        source: "country-polygons",
        filter: ["in", ["get", "id"], ["literal", this.config.countryIds || []]],
        paint: { "line-color": "#8fb6a5", "line-width": 0.7, "line-opacity": 0.55 }
      });
      safeAddLayer(this.map, {
        id: "world-arcs",
        type: "line",
        source: "world-arcs",
        paint: {
          "line-color": ["case", [">=", ["get", "balance"], 0], "#27c07e", "#e0454f"],
          "line-width": ["interpolate", ["linear"], ["get", "abs_balance"], 0, 0.6, 10000, 1.4, 300000, 4],
          "line-opacity": 0.48
        }
      });
      safeAddLayer(this.map, {
        id: "world-points",
        type: "circle",
        source: "world-points",
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["get", "abs_balance"], 0, 5, 10000, 10, 300000, 34],
          "circle-color": ["case", [">=", ["get", "balance"], 0], "#27c07e", "#e0454f"],
          "circle-opacity": 0.82,
          "circle-stroke-color": "#07120d",
          "circle-stroke-width": 1.2
        }
      });
      safeAddLayer(this.map, {
        id: "world-points-selected",
        type: "circle",
        source: "world-points",
        filter: selectedFilter(this.selected),
        paint: {
          "circle-radius": ["+", ["interpolate", ["linear"], ["get", "abs_balance"], 0, 5, 10000, 10, 300000, 34], 4],
          "circle-color": "rgba(0,0,0,0)",
          "circle-stroke-color": "#d8a93a",
          "circle-stroke-width": 3
        }
      });
      this.bindClicks(["world-points", "country-fill"]);
      this.applyCountryState();
      this.refreshSelectedFilters();
    }

    drawCustoms() {
      const points = this.config.points || { type: "FeatureCollection", features: [] };
      this.propsById = featureMap(points.features);
      this.selected = new Set(Array.from(this.selected).filter((id) => this.propsById.has(id)));
      this.ensureCountrySource();
      upsertSource(this.map, "customs-points", points);

      const metric = this.config.metric || "recaudacion";
      const colorExpr = metric === "variation"
        ? ["case", [">=", ["get", "variation"], 0], "#27c07e", "#e0454f"]
        : ["interpolate", ["linear"], ["get", "total"], 0, "#25684e", 50000, "#d8a93a", 150000, "#e0454f"];
      safeAddLayer(this.map, {
        id: "customs-points",
        type: "circle",
        source: "customs-points",
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["get", "total"], 0, 7, 50000, 17, 150000, 32],
          "circle-color": colorExpr,
          "circle-opacity": 0.86,
          "circle-stroke-color": "#07120d",
          "circle-stroke-width": 1.2
        }
      });
      safeAddLayer(this.map, {
        id: "customs-points-selected",
        type: "circle",
        source: "customs-points",
        filter: selectedFilter(this.selected),
        paint: {
          "circle-radius": ["+", ["interpolate", ["linear"], ["get", "total"], 0, 7, 50000, 17, 150000, 32], 4],
          "circle-color": "rgba(0,0,0,0)",
          "circle-stroke-color": "#d8a93a",
          "circle-stroke-width": 3
        }
      });
      this.bindClicks(["customs-points"]);
      this.refreshSelectedFilters();
    }

    bindClicks(layers) {
      if (this.boundLayers) return;
      this.boundLayers = true;
      layers.forEach((layerId) => {
        this.map.on("mouseenter", layerId, () => { this.map.getCanvas().style.cursor = "pointer"; });
        this.map.on("mouseleave", layerId, () => { this.map.getCanvas().style.cursor = ""; });
        this.map.on("click", layerId, (event) => {
          const feature = event.features && event.features[0];
          if (!feature) return;
          const rawId = String(feature.properties.id || feature.id || "");
          const id = this.propsById.has(rawId) ? rawId : String(feature.id || rawId);
          const props = this.propsById.get(id);
          if (!props) return;
          this.toggle(id);
          this.showPopup(event.lngLat, props);
        });
      });
    }

    toggle(id) {
      if (this.selected.has(id)) this.selected.delete(id);
      else this.selected.add(id);
      this.applyCountryState();
      this.refreshSelectedFilters();
      setDashInput(this.kind + "-map-event", {
        kind: this.kind,
        selected: Array.from(this.selected),
        clicked: id
      });
    }

    clear() {
      this.selected.clear();
      if (this.popup) this.popup.remove();
      this.applyCountryState();
      this.refreshSelectedFilters();
      setDashInput(this.kind + "-map-event", { kind: this.kind, selected: [], clicked: null });
    }

    applyCountryState() {
      if (this.kind !== "world" || !this.map.getSource("country-polygons")) return;
      this.propsById.forEach((props, id) => {
        try {
          this.map.setFeatureState(
            { source: "country-polygons", id: id },
            { balance: Number(props.balance || 0), selected: this.selected.has(id) }
          );
        } catch (_err) {
          // GeoJSON may not be fully indexed on first paint; the next update will apply it.
        }
      });
    }

    refreshSelectedFilters() {
      const layerId = this.kind === "world" ? "world-points-selected" : "customs-points-selected";
      if (this.map.getLayer(layerId)) this.map.setFilter(layerId, selectedFilter(this.selected));
    }

    showPopup(lngLat, props) {
      if (this.popup) this.popup.remove();
      this.popup = new maplibregl.Popup({ closeButton: false, maxWidth: "280px" })
        .setLngLat(lngLat)
        .setHTML(popupHtml(this.kind, props))
        .addTo(this.map);
    }
  }

  function scan() {
    if (!window.maplibregl) return;
    document.querySelectorAll(".maplibre-map[id]").forEach((el) => {
      const existing = bridges.get(el.id);
      if (existing) existing.updateFromDom();
      else bridges.set(el.id, new MapBridge(el));
    });
  }

  const observer = new MutationObserver(scan);
  observer.observe(document.documentElement, { childList: true, subtree: true, attributes: true, attributeFilter: ["data-config"] });
  document.addEventListener("DOMContentLoaded", scan);
  window.addEventListener("load", scan);
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-map-clear]");
    if (!button) return;
    const kind = button.getAttribute("data-map-clear");
    bridges.forEach((bridge) => {
      if (bridge.kind === kind) bridge.clear();
    });
  });
})();
