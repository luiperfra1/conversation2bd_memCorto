# triplets2bd/utils/types.py
from dataclasses import dataclass
from typing import List, Tuple, Literal, Optional, Dict, Any

Triplet = Tuple[str, str, str]
Backend = Literal["sql", "neo4j"]
Mode = Literal["hybrid", "llm", "deterministic"]

@dataclass
class EngineOptions:
    backend: Backend = "sql"
    mode: Mode = "hybrid"
    reset: bool = True
    reset_log: bool = True          # NUEVO: resetear logs por defecto
    sqlite_db_path: str = "./data/users/demo.sqlite"
    generate_report: bool = True
    report_sample_limit: int = 15
    report_path: Optional[str] = None  # si None -> <sqlite-db>_report.txt

@dataclass
class EngineResult:
    backend: Backend
    mode: Mode
    run_id: Optional[str]
    det_script: str
    llm_script: str
    executed_statements: int
    leftovers: List[Tuple[Triplet, str]]
    reset: bool
    extras: Dict[str, Any]  # incluirá extras["report_path"] si se generó
