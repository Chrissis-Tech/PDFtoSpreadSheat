"""
Data Validator
==============

Valida datos extraidos segun reglas configuradas.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


class DataValidator:
    """
    Valida datos extraidos contra reglas definidas.
    
    Funcionalidades:
    - Validacion de campos obligatorios
    - Validacion de tipos (fecha, numero, string)
    - Validacion de reglas de negocio (rangos, patrones, etc.)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicializa el validador.
        
        Args:
            config: Configuracion de validacion.
        """
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.on_error = self.config.get("on_error", "warn")  # skip, warn, fail
        self.max_errors = self.config.get("max_errors", 10)
        
        # Reglas globales
        self.global_rules = self.config.get("rules", {})
    
    def validate(
        self,
        data: List[Dict[str, Any]],
        rules: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Valida una lista de registros.
        
        Args:
            data: Lista de diccionarios a validar.
            rules: Reglas de validacion especificas del parser.
            
        Returns:
            Tupla con (datos validados, lista de errores).
        """
        if not self.enabled:
            return data, []
        
        rules = rules or {}
        validated_data = []
        errors = []
        
        for idx, row in enumerate(data):
            row_errors = self._validate_row(row, rules, idx)
            
            if row_errors:
                errors.extend(row_errors)
                
                if self.on_error == "skip":
                    continue  # Saltar fila con errores
                elif self.on_error == "fail" and len(errors) > self.max_errors:
                    raise ValueError(f"Demasiados errores de validacion: {len(errors)}")
            
            validated_data.append(row)
        
        return validated_data, errors
    
    def _validate_row(
        self,
        row: Dict[str, Any],
        rules: Dict[str, Any],
        row_idx: int
    ) -> List[str]:
        """
        Valida una fila individual.
        
        Args:
            row: Diccionario con datos de la fila.
            rules: Reglas de validacion.
            row_idx: Indice de la fila (para mensajes de error).
            
        Returns:
            Lista de errores encontrados.
        """
        errors = []
        
        # Validar cada campo con reglas especificas
        for field, field_rules in rules.items():
            if field.startswith("_"):  # Campos internos
                continue
            
            value = row.get(field)
            field_errors = self._validate_field(field, value, field_rules, row_idx)
            errors.extend(field_errors)
        
        # Aplicar reglas globales
        global_errors = self._apply_global_rules(row, row_idx)
        errors.extend(global_errors)
        
        return errors
    
    def _validate_field(
        self,
        field: str,
        value: Any,
        rules: Dict[str, Any],
        row_idx: int
    ) -> List[str]:
        """
        Valida un campo individual.
        
        Args:
            field: Nombre del campo.
            value: Valor del campo.
            rules: Reglas para el campo.
            row_idx: Indice de la fila.
            
        Returns:
            Lista de errores.
        """
        errors = []
        
        # Campo requerido
        if rules.get("required", False):
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(f"Fila {row_idx + 1}: Campo '{field}' es requerido")
                return errors  # No continuar validando si falta
        
        # Si el valor es None y no es requerido, no validar mas
        if value is None:
            return errors
        
        # Validar tipo
        expected_type = rules.get("type", "string")
        type_error = self._validate_type(field, value, expected_type, row_idx)
        if type_error:
            errors.append(type_error)
        
        # Validar rango (para numeros)
        if expected_type == "number" and isinstance(value, (int, float)):
            if "min" in rules and value < rules["min"]:
                errors.append(
                    f"Fila {row_idx + 1}: '{field}' ({value}) es menor que el minimo ({rules['min']})"
                )
            if "max" in rules and value > rules["max"]:
                errors.append(
                    f"Fila {row_idx + 1}: '{field}' ({value}) es mayor que el maximo ({rules['max']})"
                )
        
        # Validar longitud (para strings)
        if expected_type == "string" and isinstance(value, str):
            if "min_length" in rules and len(value) < rules["min_length"]:
                errors.append(
                    f"Fila {row_idx + 1}: '{field}' es muy corto (min: {rules['min_length']})"
                )
            if "max_length" in rules and len(value) > rules["max_length"]:
                errors.append(
                    f"Fila {row_idx + 1}: '{field}' es muy largo (max: {rules['max_length']})"
                )
        
        # Validar patron (regex)
        if "pattern" in rules and isinstance(value, str):
            pattern = rules["pattern"]
            if not re.match(pattern, value):
                errors.append(
                    f"Fila {row_idx + 1}: '{field}' no coincide con el patron esperado"
                )
        
        # Validar valores permitidos
        if "allowed_values" in rules:
            if value not in rules["allowed_values"]:
                errors.append(
                    f"Fila {row_idx + 1}: '{field}' tiene un valor no permitido: {value}"
                )
        
        return errors
    
    def _validate_type(
        self,
        field: str,
        value: Any,
        expected_type: str,
        row_idx: int
    ) -> Optional[str]:
        """
        Valida que el valor sea del tipo esperado.
        
        Args:
            field: Nombre del campo.
            value: Valor a validar.
            expected_type: Tipo esperado (string, number, date, boolean).
            row_idx: Indice de la fila.
            
        Returns:
            Mensaje de error o None si es valido.
        """
        if expected_type == "string":
            if not isinstance(value, str):
                return f"Fila {row_idx + 1}: '{field}' deberia ser texto"
        
        elif expected_type == "number":
            if not isinstance(value, (int, float)):
                return f"Fila {row_idx + 1}: '{field}' deberia ser numerico"
        
        elif expected_type == "date":
            if isinstance(value, str):
                # Intentar parsear la fecha
                try:
                    datetime.fromisoformat(value.replace("/", "-"))
                except ValueError:
                    return f"Fila {row_idx + 1}: '{field}' no es una fecha valida"
            elif not isinstance(value, datetime):
                return f"Fila {row_idx + 1}: '{field}' deberia ser una fecha"
        
        elif expected_type == "boolean":
            if not isinstance(value, bool):
                return f"Fila {row_idx + 1}: '{field}' deberia ser booleano"
        
        return None
    
    def _apply_global_rules(
        self,
        row: Dict[str, Any],
        row_idx: int
    ) -> List[str]:
        """
        Aplica reglas de validacion globales.
        
        Args:
            row: Fila a validar.
            row_idx: Indice de la fila.
            
        Returns:
            Lista de errores.
        """
        errors = []
        
        # Regla: Totales no negativos
        if self.global_rules.get("non_negative_totals", True):
            total_fields = ["total", "subtotal", "monto", "importe", "amount", "price"]
            for field in total_fields:
                if field in row:
                    value = row[field]
                    if isinstance(value, (int, float)) and value < 0:
                        errors.append(
                            f"Fila {row_idx + 1}: '{field}' no puede ser negativo ({value})"
                        )
        
        # Regla: Fechas validas
        if self.global_rules.get("valid_dates", True):
            date_fields = ["fecha", "date", "fecha_emision", "fecha_vencimiento"]
            for field in date_fields:
                if field in row:
                    value = row[field]
                    if isinstance(value, str) and value:
                        try:
                            # Intentar parsear
                            parsed = datetime.fromisoformat(value.replace("/", "-"))
                            # Validar rango razonable (1900-2100)
                            if parsed.year < 1900 or parsed.year > 2100:
                                errors.append(
                                    f"Fila {row_idx + 1}: '{field}' tiene un ano fuera de rango"
                                )
                        except ValueError:
                            errors.append(
                                f"Fila {row_idx + 1}: '{field}' no es una fecha valida"
                            )
        
        return errors


class ValidationRule:
    """Clase base para reglas de validacion personalizadas."""
    
    def __init__(self, name: str, message: str):
        self.name = name
        self.message = message
    
    def validate(self, value: Any, row: Dict[str, Any]) -> bool:
        """
        Valida un valor.
        
        Args:
            value: Valor a validar.
            row: Fila completa (para validaciones cruzadas).
            
        Returns:
            True si es valido, False si no.
        """
        raise NotImplementedError


class NonNegativeRule(ValidationRule):
    """Regla: El valor no puede ser negativo."""
    
    def __init__(self):
        super().__init__("non_negative", "El valor no puede ser negativo")
    
    def validate(self, value: Any, row: Dict[str, Any]) -> bool:
        if isinstance(value, (int, float)):
            return value >= 0
        return True


class RequiredRule(ValidationRule):
    """Regla: El campo es obligatorio."""
    
    def __init__(self):
        super().__init__("required", "El campo es obligatorio")
    
    def validate(self, value: Any, row: Dict[str, Any]) -> bool:
        if value is None:
            return False
        if isinstance(value, str) and not value.strip():
            return False
        return True


class RangeRule(ValidationRule):
    """Regla: El valor debe estar dentro de un rango."""
    
    def __init__(self, min_val: Optional[float] = None, max_val: Optional[float] = None):
        super().__init__("range", f"El valor debe estar entre {min_val} y {max_val}")
        self.min_val = min_val
        self.max_val = max_val
    
    def validate(self, value: Any, row: Dict[str, Any]) -> bool:
        if not isinstance(value, (int, float)):
            return True
        
        if self.min_val is not None and value < self.min_val:
            return False
        if self.max_val is not None and value > self.max_val:
            return False
        
        return True
