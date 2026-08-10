"""
Servicio de datos - Orquesta API calls y transformacion de datos
"""
import json
import os
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from .api import BanxicoClient
from .comex import db
from .comex import warehouse
from .models import Serie, DatosComercio
from series_catalog import SERIES


class DataService:
    """Servicio centralizado para gestionar datos"""

    CACHE_FILE = Path(__file__).resolve().parents[1] / "data" / "comercio_exterior.json"
    LIVE_REFRESH_SECONDS = int(os.environ.get("LIVE_REFRESH_SECONDS", "900"))
    LIVE_BOOTSTRAP = os.environ.get("LIVE_BOOTSTRAP", "0").strip().lower() in {"1", "true", "yes"}

    def __init__(self):
        """Inicializa el servicio"""
        self.client: Optional[BanxicoClient] = None
        self._memory_cache: Optional[DatosComercio] = None
        self._memory_cache_loaded_at: Optional[datetime] = None
        self._static_cache: Optional[DatosComercio] = None
        self._static_cache_mtime: Optional[float] = None
        self._try_init_client()

    def _try_init_client(self):
        """Intenta inicializar cliente Banxico"""
        try:
            self.client = BanxicoClient()
        except ValueError as e:
            db.record_error("data_service.init_client", e)
            print(f"[ADVERTENCIA] {e}")
            self.client = None

    @staticmethod
    def display_datetime(value: datetime | str | None) -> str:
        """Formato visible en espanol con fecha larga y hora completa."""
        if value is None:
            return "n.d."
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return value.replace("T", " ")
        months = {
            1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
            5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
            9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
        }
        return f"{value.day} de {months[value.month]} {value.year} {value:%H:%M:%S}"

    def get_live_data(self) -> Optional[DatosComercio]:
        """Descarga datos EN VIVO desde API Banxico"""
        if not self.client:
            print("[FALLBACK] Cliente API no disponible")
            return None

        try:
            print("[API] Descargando datos en vivo...")
            series_ids = list(SERIES.keys())
            raw_series = self.client.get_series(series_ids)

            # Transformar datos
            series_list = []
            for sid in series_ids:
                datos = raw_series.get(sid, [])
                if sid not in SERIES:
                    continue
                info = SERIES[sid]
                fechas = []
                valores = []
                for d in datos:
                    fecha = self.client._parse_date(d.get("fecha", ""))
                    valor = self.client._parse_value(d.get("dato"))
                    if fecha and valor is not None:
                        fechas.append(fecha)
                        valores.append(valor)

                if fechas:
                    puntos = sorted(zip(fechas, valores), key=lambda item: item[0])
                    series_list.append(Serie(
                        nombre=info["nombre"],
                        serie_id=sid,
                        flujo=info["flujo"],
                        grupo=info["grupo"],
                        fechas=[fecha for fecha, _ in puntos],
                        valores=[valor for _, valor in puntos],
                    ))

            print(f"[OK] {len(series_list)} series descargadas")

            # Cargar datos estaticos del cache
            cached = self._load_cached_data()
            if cached:
                cached.series = series_list
                cached.actualizado = datetime.now()
                cached.completo = True
                return cached

            return None

        except Exception as e:
            db.record_error("data_service.live_banxico", e)
            print(f"[ERROR] {e}")
            return None

    def get_cached_data(self) -> Optional[DatosComercio]:
        """Carga el estado local: DuckDB primero, JSON solo como fallback/migracion."""
        sql_data = self._load_sql_data()
        if sql_data:
            return sql_data

        migrated = warehouse.load_json_cache_to_warehouse(self.CACHE_FILE)
        if migrated.get("status") == "ok":
            sql_data = self._load_sql_data()
            if sql_data:
                return sql_data

        return self._load_cached_data()

    def _load_sql_data(self) -> Optional[DatosComercio]:
        """Carga el dashboard desde DuckDB, que es la fuente primaria local."""
        try:
            return warehouse.load_dashboard_from_warehouse()
        except Exception as e:
            db.record_error("data_service.load_warehouse", e)
            print(f"[ERROR] Cargando DuckDB warehouse: {e}")
            return None

    def _load_cached_data(self) -> Optional[DatosComercio]:
        """Carga y parsea archivo JSON en cache"""
        try:
            cache_file = self.CACHE_FILE
            if not cache_file.exists():
                print(f"[ERROR] {cache_file} no existe")
                return None

            mtime = cache_file.stat().st_mtime
            if self._static_cache and self._static_cache_mtime == mtime:
                return deepcopy(self._static_cache)

            with cache_file.open(encoding="utf-8") as f:
                data = json.load(f)

            # Transformar series
            series_list = [
                Serie(
                    nombre=s["nombre"],
                    serie_id=s.get("serie_id", s.get("idSerie", "")),
                    flujo=s["flujo"],
                    grupo=s["grupo"],
                    fechas=s["fechas"],
                    valores=s["valores"]
                )
                for s in data.get("series", [])
            ]

            actualizado_raw = data.get("actualizado", datetime.now().isoformat())
            if isinstance(actualizado_raw, str) and len(actualizado_raw) == 10:
                actualizado_raw = datetime.fromtimestamp(mtime).isoformat(timespec="seconds")

            parsed = DatosComercio(
                fuente=data.get("fuente", ""),
                actualizado=datetime.fromisoformat(actualizado_raw),
                completo=data.get("completo", False),
                series=series_list,
                anual=data.get("anual", {}),
                acumulado=data.get("acumulado", {}),
                paises_balanza=data.get("paises_balanza", []),
                aduanas=data.get("aduanas", []),
                industrias_exportacion=data.get("industrias_exportacion", []),
                importaciones_uso=data.get("importaciones_uso", []),
                balanza_componentes=data.get("balanza_componentes", []),
                recaudacion_aduanas=data.get("recaudacion_aduanas"),
            )
            self._static_cache = parsed
            self._static_cache_mtime = mtime
            return deepcopy(parsed)

        except Exception as e:
            db.record_error("data_service.load_json_cache", e, str(self.CACHE_FILE))
            print(f"[ERROR] Cargando cache: {e}")
            return None

    def _cache_is_fresh(self) -> bool:
        """Devuelve True si el cache en memoria todavia es reutilizable."""
        if not self._memory_cache or not self._memory_cache_loaded_at:
            return False
        return datetime.now() - self._memory_cache_loaded_at < timedelta(
            seconds=self.LIVE_REFRESH_SECONDS
        )

    def get_data(self, force_refresh: bool = False) -> DatosComercio:
        """
        Obtiene datos priorizando: memoria > DuckDB > API en vivo > JSON fallback.
        """
        if not force_refresh and self._cache_is_fresh():
            return self._memory_cache

        cached_data = self.get_cached_data()
        if cached_data and not force_refresh and not self.LIVE_BOOTSTRAP:
            self._memory_cache = cached_data
            self._memory_cache_loaded_at = datetime.now()
            return cached_data

        live_data = self.get_live_data()
        if live_data:
            try:
                warehouse.save_dashboard_to_warehouse(
                    live_data,
                    source_code="banxico-api",
                    source_file="Banxico API",
                )
                warehouse.export_warehouse_to_json(self.CACHE_FILE)
            except Exception as e:
                db.record_error("data_service.save_live_warehouse", e)
                print(f"[ADVERTENCIA] No se pudo actualizar DuckDB warehouse: {e}")
            self._memory_cache = live_data
            self._memory_cache_loaded_at = datetime.now()
            return live_data

        if cached_data:
            print("[FALLBACK] Usando datos en cache")
            self._memory_cache = cached_data
            self._memory_cache_loaded_at = datetime.now()
            return cached_data

        # Error critico
        raise RuntimeError(
            "No se pudieron cargar datos. "
            "Verifica: token.txt, API de Banxico, o data/comercio_exterior.json"
        )
