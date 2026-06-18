# Purpose: Provides conservative, traceable learning from qualified additive-manufacturing builds.
# Reason: Company process recommendations must stay inside measured experience and expose uncertainty.
"""Data contracts and a lightweight process-recommendation engine for MiniSlicer.

The engine intentionally does not generate toolpaths or machine code. It learns
from completed, quality-reviewed builds and recommends process parameters only
when the requested job is sufficiently close to qualified historical evidence.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np

SCHEMA_VERSION = 1
MIN_TRAINING_BUILDS = 12
DEFAULT_NEIGHBORS = 5

FEATURE_NAMES = (
    "part_volume_cm3",
    "surface_area_cm2",
    "height_mm",
    "max_section_mm",
    "wall_thickness_mm",
    "overhang_fraction",
    "wire_diameter_mm",
    "layer_height_mm",
)

TARGET_NAMES = (
    "travel_speed_mm_s",
    "wire_feed_m_min",
    "arc_current_a",
    "arc_voltage_v",
    "interpass_limit_c",
)


@dataclass(frozen=True)
class BuildFeatures:
    """Geometry and fixed process context known before parameter selection."""

    part_volume_cm3: float
    surface_area_cm2: float
    height_mm: float
    max_section_mm: float
    wall_thickness_mm: float
    overhang_fraction: float
    wire_diameter_mm: float
    layer_height_mm: float

    def vector(self) -> np.ndarray:
        values = np.asarray([getattr(self, name) for name in FEATURE_NAMES], dtype=np.float64)
        if not np.all(np.isfinite(values)):
            raise ValueError("Build features must contain only finite values.")
        if np.any(values[:5] <= 0) or self.wire_diameter_mm <= 0 or self.layer_height_mm <= 0:
            raise ValueError("Geometry dimensions, wire diameter, and layer height must be positive.")
        if not 0.0 <= self.overhang_fraction <= 1.0:
            raise ValueError("overhang_fraction must be between 0 and 1.")
        return values


@dataclass(frozen=True)
class ProcessParameters:
    """Controllable DED process settings recorded for a completed build."""

    travel_speed_mm_s: float
    wire_feed_m_min: float
    arc_current_a: float
    arc_voltage_v: float
    interpass_limit_c: float

    def vector(self) -> np.ndarray:
        values = np.asarray([getattr(self, name) for name in TARGET_NAMES], dtype=np.float64)
        if not np.all(np.isfinite(values)) or np.any(values <= 0):
            raise ValueError("Process parameters must be finite and positive.")
        return values


@dataclass(frozen=True)
class QualityOutcome:
    """Measured build outcome used to decide whether a recipe is trustworthy."""

    accepted: bool
    dimensional_error_mm: float
    porosity_pct: float
    surface_roughness_ra_um: float
    deposition_efficiency_pct: float
    interruption_count: int = 0

    def quality_weight(self) -> float:
        """Return a bounded evidence weight; rejected builds do not become recipes."""
        if not self.accepted:
            return 0.0
        penalties = (
            min(max(self.dimensional_error_mm, 0.0) / 2.0, 1.0) * 0.30
            + min(max(self.porosity_pct, 0.0) / 2.0, 1.0) * 0.30
            + min(max(self.surface_roughness_ra_um, 0.0) / 80.0, 1.0) * 0.15
            + min(max(100.0 - self.deposition_efficiency_pct, 0.0) / 30.0, 1.0) * 0.15
            + min(max(self.interruption_count, 0) / 4.0, 1.0) * 0.10
        )
        return max(0.05, 1.0 - penalties)


@dataclass(frozen=True)
class BuildRecord:
    """One traceable, completed build suitable for model training."""

    build_id: str
    machine_id: str
    material_id: str
    material_batch_id: str
    geometry_family: str
    started_at: str
    features: BuildFeatures
    parameters: ProcessParameters
    outcome: QualityOutcome
    plan_fingerprint: str = ""
    schema_version: int = SCHEMA_VERSION

    def validate(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"Unsupported build-record schema version: {self.schema_version}")
        for field_name in (
            "build_id",
            "machine_id",
            "material_id",
            "material_batch_id",
            "geometry_family",
            "started_at",
        ):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} is required.")
        self.features.vector()
        self.parameters.vector()
        try:
            datetime.fromisoformat(self.started_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("started_at must be an ISO-8601 timestamp.") from exc

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "BuildRecord":
        record = cls(
            build_id=str(payload["build_id"]),
            machine_id=str(payload["machine_id"]),
            material_id=str(payload["material_id"]),
            material_batch_id=str(payload["material_batch_id"]),
            geometry_family=str(payload["geometry_family"]),
            started_at=str(payload["started_at"]),
            plan_fingerprint=str(payload.get("plan_fingerprint", "")),
            schema_version=int(payload.get("schema_version", SCHEMA_VERSION)),
            features=BuildFeatures(**payload["features"]),
            parameters=ProcessParameters(**payload["parameters"]),
            outcome=QualityOutcome(**payload["outcome"]),
        )
        record.validate()
        return record


@dataclass(frozen=True)
class ParameterEnvelope:
    """Engineer-approved hard limits that recommendations may never exceed."""

    minimum: ProcessParameters
    maximum: ProcessParameters

    def clamp(self, vector: np.ndarray) -> tuple[np.ndarray, tuple[str, ...]]:
        low = self.minimum.vector()
        high = self.maximum.vector()
        if np.any(low > high):
            raise ValueError("Parameter-envelope minimum exceeds maximum.")
        clipped = np.clip(vector, low, high)
        changed = tuple(
            TARGET_NAMES[index]
            for index in range(len(TARGET_NAMES))
            if not math.isclose(float(vector[index]), float(clipped[index]), rel_tol=1e-9, abs_tol=1e-9)
        )
        return clipped, changed


@dataclass(frozen=True)
class ProcessRecommendation:
    """Recommendation plus evidence and applicability signals."""

    status: str
    parameters: ProcessParameters | None
    confidence: float
    applicability_distance: float
    evidence_build_ids: tuple[str, ...]
    warnings: tuple[str, ...]


class ProcessRecommendationEngine:
    """Quality-weighted nearest-neighbor estimator with applicability gating."""

    def __init__(
        self,
        *,
        neighbors: int = DEFAULT_NEIGHBORS,
        max_applicability_distance: float = 3.0,
    ) -> None:
        if neighbors < 1:
            raise ValueError("neighbors must be positive.")
        if max_applicability_distance <= 0:
            raise ValueError("max_applicability_distance must be positive.")
        self.neighbors = int(neighbors)
        self.max_applicability_distance = float(max_applicability_distance)
        self._records: list[BuildRecord] = []
        self._feature_matrix: np.ndarray | None = None
        self._target_matrix: np.ndarray | None = None
        self._means: np.ndarray | None = None
        self._stds: np.ndarray | None = None
        self._quality_weights: np.ndarray | None = None

    @property
    def training_build_count(self) -> int:
        return len(self._records)

    def fit(
        self,
        records: Iterable[BuildRecord],
        *,
        machine_id: str,
        material_id: str,
    ) -> "ProcessRecommendationEngine":
        qualified: list[BuildRecord] = []
        for record in records:
            record.validate()
            if (
                record.machine_id == machine_id
                and record.material_id == material_id
                and record.outcome.quality_weight() > 0.0
            ):
                qualified.append(record)

        if len(qualified) < MIN_TRAINING_BUILDS:
            raise ValueError(
                f"At least {MIN_TRAINING_BUILDS} accepted builds are required for one machine/material pair."
            )

        features = np.vstack([record.features.vector() for record in qualified])
        targets = np.vstack([record.parameters.vector() for record in qualified])
        means = features.mean(axis=0)
        stds = features.std(axis=0)
        stds = np.where(stds < 1e-9, 1.0, stds)

        self._records = qualified
        self._feature_matrix = features
        self._target_matrix = targets
        self._means = means
        self._stds = stds
        self._quality_weights = np.asarray(
            [record.outcome.quality_weight() for record in qualified],
            dtype=np.float64,
        )
        return self

    def recommend(
        self,
        features: BuildFeatures,
        *,
        envelope: ParameterEnvelope,
    ) -> ProcessRecommendation:
        if self._feature_matrix is None or self._target_matrix is None:
            raise RuntimeError("Fit the recommendation engine before requesting recommendations.")
        assert self._means is not None
        assert self._stds is not None
        assert self._quality_weights is not None

        query = features.vector()
        standardized = (self._feature_matrix - self._means) / self._stds
        query_standardized = (query - self._means) / self._stds
        distances = np.linalg.norm(standardized - query_standardized, axis=1)
        neighbor_count = min(self.neighbors, len(self._records))
        indexes = np.argsort(distances, kind="stable")[:neighbor_count]
        nearest_distance = float(distances[indexes[0]])
        evidence_ids = tuple(self._records[index].build_id for index in indexes)

        if nearest_distance > self.max_applicability_distance:
            return ProcessRecommendation(
                status="Insufficient evidence",
                parameters=None,
                confidence=0.0,
                applicability_distance=nearest_distance,
                evidence_build_ids=evidence_ids,
                warnings=(
                    "Requested job is outside the validated machine/material experience.",
                    "Run a supervised development build and qualify the result before enabling recommendations.",
                ),
            )

        distance_weights = 1.0 / np.maximum(distances[indexes], 0.05)
        weights = distance_weights * self._quality_weights[indexes]
        prediction = np.average(self._target_matrix[indexes], axis=0, weights=weights)
        clamped, changed = envelope.clamp(prediction)
        spread = np.average(
            np.abs(self._target_matrix[indexes] - prediction),
            axis=0,
            weights=weights,
        )
        relative_spread = float(np.mean(spread / np.maximum(np.abs(prediction), 1e-6)))
        distance_confidence = max(0.0, 1.0 - nearest_distance / self.max_applicability_distance)
        confidence = max(0.0, min(1.0, distance_confidence * (1.0 - min(relative_spread, 1.0))))

        warnings: list[str] = []
        if changed:
            warnings.append("Recommendation was clamped to engineer-approved limits: " + ", ".join(changed))
        if confidence < 0.6:
            warnings.append("Evidence is variable; require an engineering review and monitored trial build.")

        return ProcessRecommendation(
            status="Recommend" if confidence >= 0.6 else "Engineering review",
            parameters=_parameters_from_vector(clamped),
            confidence=confidence,
            applicability_distance=nearest_distance,
            evidence_build_ids=evidence_ids,
            warnings=tuple(warnings),
        )


def save_build_record_jsonl(path: str | Path, record: BuildRecord) -> None:
    """Append one validated build record to an auditable JSONL dataset."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record.to_dict(), sort_keys=True, separators=(",", ":"))
    with target.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line + "\n")


def load_build_records_jsonl(path: str | Path) -> list[BuildRecord]:
    """Load and validate all build records from a JSONL dataset."""
    source = Path(path)
    if not source.exists():
        return []
    return parse_build_records_jsonl(source.read_text(encoding="utf-8"))


def parse_build_records_jsonl(text: str) -> list[BuildRecord]:
    """Parse and validate build records supplied as JSONL text."""
    records: list[BuildRecord] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(BuildRecord.from_dict(json.loads(line)))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid build record at line {line_number}: {exc}") from exc
    return records


def grouped_time_split(
    records: Iterable[BuildRecord],
    *,
    test_fraction: float = 0.2,
) -> tuple[list[BuildRecord], list[BuildRecord]]:
    """Split complete builds chronologically; no layer or sample can cross the boundary."""
    if not 0.05 <= test_fraction <= 0.5:
        raise ValueError("test_fraction must be between 0.05 and 0.5.")
    rows = list(records)
    for record in rows:
        record.validate()
    rows.sort(key=lambda record: (record.started_at, record.build_id))
    if len(rows) < 2:
        return rows, []
    split_index = min(max(int(len(rows) * (1.0 - test_fraction)), 1), len(rows) - 1)
    return rows[:split_index], rows[split_index:]


def dataset_summary(records: Iterable[BuildRecord]) -> dict[str, Any]:
    """Return compact coverage and quality statistics for release dashboards."""
    rows = list(records)
    accepted = [record for record in rows if record.outcome.accepted]
    return {
        "schema_version": SCHEMA_VERSION,
        "build_count": len(rows),
        "accepted_build_count": len(accepted),
        "rejected_build_count": len(rows) - len(accepted),
        "machine_count": len({record.machine_id for record in rows}),
        "material_count": len({record.material_id for record in rows}),
        "geometry_family_count": len({record.geometry_family for record in rows}),
        "latest_build_at": max((record.started_at for record in rows), default=None),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def evaluate_recommendation_engine(
    records: Iterable[BuildRecord],
    *,
    neighbors: int = DEFAULT_NEIGHBORS,
    max_applicability_distance: float = 3.0,
    test_fraction: float = 0.2,
) -> dict[str, Any]:
    """Evaluate parameter recommendations on complete, chronologically unseen builds."""
    rows = list(records)
    train, test = grouped_time_split(rows, test_fraction=test_fraction)
    if len(train) < MIN_TRAINING_BUILDS or not test:
        return {
            "status": "insufficient_evaluation_data",
            "train_builds": len(train),
            "test_builds": len(test),
            "recommended_builds": 0,
            "coverage": 0.0,
            "mae": {},
        }

    machine_ids = {record.machine_id for record in rows}
    material_ids = {record.material_id for record in rows}
    if len(machine_ids) != 1 or len(material_ids) != 1:
        raise ValueError("Evaluation records must belong to one machine/material domain.")
    machine_id = next(iter(machine_ids))
    material_id = next(iter(material_ids))
    engine = ProcessRecommendationEngine(
        neighbors=neighbors,
        max_applicability_distance=max_applicability_distance,
    ).fit(train, machine_id=machine_id, material_id=material_id)

    training_targets = np.vstack([record.parameters.vector() for record in train])
    envelope = ParameterEnvelope(
        minimum=_parameters_from_vector(training_targets.min(axis=0)),
        maximum=_parameters_from_vector(training_targets.max(axis=0)),
    )
    absolute_errors: list[np.ndarray] = []
    confidence_values: list[float] = []
    for record in test:
        recommendation = engine.recommend(record.features, envelope=envelope)
        if recommendation.parameters is None:
            continue
        absolute_errors.append(
            np.abs(recommendation.parameters.vector() - record.parameters.vector())
        )
        confidence_values.append(recommendation.confidence)

    if not absolute_errors:
        return {
            "status": "no_test_recommendations",
            "train_builds": len(train),
            "test_builds": len(test),
            "recommended_builds": 0,
            "coverage": 0.0,
            "mean_confidence": 0.0,
            "mae": {},
        }

    errors = np.vstack(absolute_errors)
    return {
        "status": "evaluated",
        "train_builds": len(train),
        "test_builds": len(test),
        "recommended_builds": len(absolute_errors),
        "coverage": len(absolute_errors) / len(test),
        "mean_confidence": float(np.mean(confidence_values)),
        "mae": {
            name: float(errors[:, index].mean())
            for index, name in enumerate(TARGET_NAMES)
        },
    }


def _parameters_from_vector(vector: np.ndarray) -> ProcessParameters:
    return ProcessParameters(**{
        name: float(vector[index])
        for index, name in enumerate(TARGET_NAMES)
    })
