"""Pool water chemistry targets and the starter care schedule.

General product knowledge, not household specifics (D15): the target ranges below are the
widely published domestic-pool figures, varying by how the pool is sanitised and what it is
built from. They exist so a household that has never looked after a pool can read a test strip
and know whether the number is fine, and what to do when it is not.

Treat these as a starting point, not a substitute for a pool shop's water analysis — the
guidance strings say so where it matters.
"""
from __future__ import annotations

from decimal import Decimal


def _d(value) -> Decimal:
    return Decimal(str(value))


# --- Water tests -----------------------------------------------------------------------
#
# Each entry: the reading's label, its unit, the target band, why it matters, and what to do
# when a result sits below or above the band.

READINGS = {
    "free_chlorine": {
        "label": "Free chlorine",
        "unit": "ppm",
        "range": (1.0, 3.0),
        "why": "The sanitiser actually available to kill bacteria and algae. Everything else is "
               "in service of keeping this working.",
        "low": "Run the chlorinator or filter longer, or add chlorine. Persistent lows in a salt "
               "pool usually mean the cell needs cleaning, the output is set too low, or the "
               "stabiliser has dropped.",
        "high": "Stop dosing and leave the cover off; sunlight brings it down within a day or "
                "two. Swim once it is back under 3 ppm.",
    },
    "ph": {
        "label": "pH",
        "unit": "",
        "range": (7.2, 7.6),
        "why": "How acidic or alkaline the water is. Outside the band, chlorine stops working "
               "properly and the water starts to sting eyes or corrode fittings.",
        "low": "Acidic water corrodes metal fittings and can etch the surface. Add a pH increaser "
               "(soda ash) in small doses and retest after a full circulation cycle.",
        "high": "Chlorine loses much of its punch and the water can go cloudy or scale up. Add a "
                "pH reducer (dry acid or hydrochloric acid) in small doses and retest. Salt pools "
                "drift upward on their own, so expect to do this regularly.",
    },
    "total_alkalinity": {
        "label": "Total alkalinity",
        "unit": "ppm",
        "range": (80.0, 120.0),
        "why": "The buffer that stops pH bouncing around. Get this right before chasing pH.",
        "low": "pH will swing with every dose or rain shower. Add an alkalinity increaser "
               "(sodium bicarbonate), then recheck pH.",
        "high": "pH becomes stubborn and the water can cloud or scale. Lower it slowly with acid, "
                "in stages, retesting between.",
    },
    "calcium_hardness": {
        "label": "Calcium hardness",
        "unit": "ppm",
        "range": (200.0, 400.0),
        "why": "How much dissolved calcium the water holds. Water low in calcium will take it "
               "out of the pool's own surface instead.",
        "low": "Soft water etches concrete and grout. Add a calcium hardness increaser.",
        "high": "Expect scale on the waterline, the salt cell and the heater. Usually corrected "
                "by partially draining and refilling with fresh water.",
    },
    "cyanuric_acid": {
        "label": "Stabiliser (cyanuric acid)",
        "unit": "ppm",
        "range": (30.0, 50.0),
        "why": "Sunscreen for the chlorine. Without it, a sunny day destroys most of your "
               "chlorine within hours.",
        "low": "Chlorine burns off in sunlight almost as fast as it is made. Add stabiliser and "
               "retest in a few days — it dissolves slowly.",
        "high": "Chlorine becomes sluggish and tests can read fine while the water is not really "
                "protected. The only real fix is partially draining and refilling.",
    },
    "salt": {
        "label": "Salt",
        "unit": "ppm",
        "range": (3000.0, 4500.0),
        "why": "The stock your chlorinator makes chlorine from. Too little and it cannot keep "
               "up; too much and the cell can be damaged.",
        "low": "The chlorinator will underproduce or alarm. Add pool salt with the pump running "
               "and retest after a full day of circulation.",
        "high": "Water tastes salty and the cell can suffer. Correct by partially draining and "
                "refilling with fresh water.",
    },
    "water_temp_c": {
        "label": "Water temperature",
        "unit": "°C",
        "range": None,  # Informational: it explains the other readings rather than being a target.
        "why": "Warm water uses chlorine faster and grows algae faster, so a hot week usually "
               "means more sanitiser and more filtering, not a broken chlorinator.",
        "low": "",
        "high": "",
    },
}

# Sanitiser and surface change a few of the bands.
_SANITISER_OVERRIDES = {
    # Salt pools run more stabiliser because the cell trickles chlorine in all day.
    "saltwater": {"cyanuric_acid": (40.0, 80.0)},
    # Only a salt pool has salt to measure.
    "chlorine": {"salt": None},
    "mineral": {"cyanuric_acid": (40.0, 80.0)},
    "bromine": {"free_chlorine": (2.0, 4.0), "cyanuric_acid": None, "salt": None},
    "other": {},
}
_SURFACE_OVERRIDES = {
    # Fibreglass and vinyl have no calcium of their own for soft water to attack.
    "fibreglass": {"calcium_hardness": (100.0, 250.0)},
    "vinyl_liner": {"calcium_hardness": (100.0, 250.0)},
}


def targets_for(sanitiser: str, surface: str = "") -> dict:
    """The applicable target bands, as `{reading: {label, unit, min, max, why, low, high}}`.

    A reading whose band is `None` does not apply to this pool (salt in a chlorine pool) and is
    left out entirely, so the UI never asks for a number that means nothing here.
    """
    overrides = {**_SANITISER_OVERRIDES.get(sanitiser, {}), **_SURFACE_OVERRIDES.get(surface, {})}
    result = {}
    for key, spec in READINGS.items():
        band = overrides[key] if key in overrides else spec["range"]
        if key in overrides and band is None and spec["range"] is not None:
            continue  # Not measured on this kind of pool.
        result[key] = {
            "label": spec["label"], "unit": spec["unit"],
            "min": None if band is None else _d(band[0]),
            "max": None if band is None else _d(band[1]),
            "why": spec["why"], "low": spec["low"], "high": spec["high"],
        }
    return result


def assess(values: dict, sanitiser: str, surface: str = "") -> dict:
    """Score one set of readings against the targets.

    Returns `{reading: {status, label, unit, value, min, max, advice}}` for every reading that
    was actually entered — `status` is `ok`, `low`, `high` or `info`.
    """
    targets = targets_for(sanitiser, surface)
    assessed = {}
    for key, target in targets.items():
        value = values.get(key)
        if value is None:
            continue
        status = "info"
        advice = ""
        if target["min"] is not None and target["max"] is not None:
            if _d(value) < target["min"]:
                status, advice = "low", target["low"]
            elif _d(value) > target["max"]:
                status, advice = "high", target["high"]
            else:
                status = "ok"
        assessed[key] = {
            "status": status, "label": target["label"], "unit": target["unit"],
            "value": _d(value), "min": target["min"], "max": target["max"],
            "advice": advice, "why": target["why"],
        }
    return assessed


# --- Starter care schedule -------------------------------------------------------------
#
# One RRULE per job (D8). `salt_only` jobs are created only where a cell is doing the work.
# The notes exist to teach: each says what the job is for, not just that it is due.

CARE_SCHEDULE = [
    {
        "title": "Skim the surface and empty the skimmer baskets",
        "recurrence_rule": "RRULE:FREQ=WEEKLY",
        "notes": "Leaves left to sink become the food supply for algae, and a full basket starves "
                 "the pump of flow. The single highest-value five minutes in pool care.",
    },
    {
        "title": "Test chlorine and pH",
        "recurrence_rule": "RRULE:FREQ=WEEKLY",
        "notes": "The two numbers that decide whether the water is safe this week. Strips are "
                 "fine for a weekly check; get a proper shop test occasionally to keep them honest.",
    },
    {
        "title": "Brush the walls, steps and waterline",
        "recurrence_rule": "RRULE:FREQ=WEEKLY",
        "notes": "Algae takes hold in the corners and behind the steps where the flow does not "
                 "reach. Brushing lifts it before it can establish.",
    },
    {
        "title": "Vacuum the floor",
        "recurrence_rule": "RRULE:FREQ=WEEKLY;INTERVAL=2",
        "notes": "Removes the fine silt that clouds the water and consumes chlorine.",
    },
    {
        "title": "Empty the pump basket",
        "recurrence_rule": "RRULE:FREQ=WEEKLY;INTERVAL=2",
        "notes": "Turn the pump off first. A blocked basket makes the pump work hard for very "
                 "little flow, and running one dry can destroy the seal.",
    },
    {
        "title": "Full water test: alkalinity, stabiliser, calcium and salt",
        "recurrence_rule": "RRULE:FREQ=MONTHLY",
        "notes": "The slow-moving numbers. Alkalinity and stabiliser are what keep the weekly pH "
                 "and chlorine readings stable, so correct these before chasing the weekly ones.",
    },
    {
        "title": "Backwash or clean the filter",
        "recurrence_rule": "RRULE:FREQ=MONTHLY",
        "notes": "Do it when the pressure gauge sits about 60–70 kPa above its clean reading, "
                 "rather than strictly by the calendar. A cartridge filter is rinsed, not "
                 "backwashed.",
    },
    {
        "title": "Inspect and clean the salt cell",
        "recurrence_rule": "RRULE:FREQ=MONTHLY;INTERVAL=3",
        "salt_only": True,
        "notes": "Scale on the plates is the usual reason a salt pool stops holding chlorine. "
                 "Inspect it, and only clean it when you can see build-up — acid washing a cell "
                 "that does not need it shortens its life.",
    },
    {
        "title": "Check the water level",
        "recurrence_rule": "RRULE:FREQ=WEEKLY;INTERVAL=2",
        "notes": "Keep it around the middle of the skimmer mouth. Too low and the pump draws air; "
                 "too high and the skimmer stops skimming.",
    },
    {
        "title": "Service the pump, filter and chlorinator",
        "recurrence_rule": "RRULE:FREQ=YEARLY",
        "notes": "The annual professional look-over: seals, bearings, cell condition and the "
                 "settings that have drifted over a season.",
    },
]


def schedule_for(sanitiser: str) -> list[dict]:
    """The starter jobs that apply to this pool, in the order they should be created."""
    has_cell = sanitiser in ("saltwater", "mineral")
    return [job for job in CARE_SCHEDULE if has_cell or not job.get("salt_only")]
