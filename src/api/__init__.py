"""
Cliente API para Banxico SIE
"""
import os
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime


class BanxicoClient:
    """Cliente para descargar datos del SIE Banxico"""

    BASE_URL = "https://www.banxico.org.mx/SieAPIRest/service/v1"
    BATCH_SIZE = 10
    TIMEOUT = 60

    def __init__(self, token: Optional[str] = None):
        """Inicializa cliente con token"""
        self.token = token or self._read_token()
        if not self.token:
            raise ValueError(
                "[ERROR] Token requerido. Ver README.md"
            )
        self.headers = {
            "Bmx-Token": self.token,
            "Accept": "application/json"
        }

    @staticmethod
    def _read_token() -> Optional[str]:
        """Lee token de env o archivo token.txt"""
        if env_token := os.environ.get("BANXICO_TOKEN"):
            return env_token.strip()
        token_file = os.path.join(os.path.dirname(__file__), "..", "..", "token.txt")
        if os.path.exists(token_file):
            with open(token_file, encoding="utf-8") as f:
                return f.read().strip()
        return None

    def get_series(self, series_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Descarga datos de series desde API Banxico"""
        result = {}

        for i in range(0, len(series_ids), self.BATCH_SIZE):
            batch = series_ids[i:i + self.BATCH_SIZE]
            try:
                response = requests.get(
                    f"{self.BASE_URL}/series/{','.join(batch)}/datos",
                    headers=self.headers,
                    timeout=self.TIMEOUT,
                    verify=True,
                )
                response.raise_for_status()

                data = response.json()
                for serie in data.get("bmx", {}).get("series", []):
                    serie_id = serie["idSerie"]
                    result[serie_id] = serie.get("datos", [])

            except requests.exceptions.RequestException as e:
                print(f"[ERROR] Banxico API: {e}")
                raise RuntimeError(f"Error consultando API: {e}")

        return result

    @staticmethod
    def _parse_value(value: Any) -> Optional[float]:
        """Convierte string a float"""
        if value in (None, "", "N/E", "NA"):
            return None
        try:
            return float(str(value).replace(",", ""))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_date(date_str: str) -> str:
        """Convierte fecha a formato YYYY-MM-DD"""
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return date_str
