"""
Dataclasses para modelos de datos
"""
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from datetime import datetime


@dataclass
class Serie:
    """Modelo de serie economica del SIE"""
    nombre: str
    serie_id: str
    flujo: str
    grupo: str
    fechas: List[str]
    valores: List[Optional[float]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nombre": self.nombre,
            "serie_id": self.serie_id,
            "flujo": self.flujo,
            "grupo": self.grupo,
            "fechas": self.fechas,
            "valores": self.valores,
        }


@dataclass
class DatosComercio:
    """Modelo principal de datos de comercio exterior"""
    fuente: str
    actualizado: datetime
    completo: bool
    series: List[Serie]
    anual: Dict[str, float]
    acumulado: Dict[str, Any]
    paises_balanza: List[List]
    aduanas: List[List]
    industrias_exportacion: List[List]
    importaciones_uso: List[List]
    balanza_componentes: List[List]
    recaudacion_aduanas: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fuente": self.fuente,
            "actualizado": self.actualizado.isoformat(),
            "completo": self.completo,
            "series": [s.to_dict() for s in self.series],
            "anual": self.anual,
            "acumulado": self.acumulado,
            "paises_balanza": self.paises_balanza,
            "aduanas": self.aduanas,
            "industrias_exportacion": self.industrias_exportacion,
            "importaciones_uso": self.importaciones_uso,
            "balanza_componentes": self.balanza_componentes,
            "recaudacion_aduanas": self.recaudacion_aduanas,
        }
