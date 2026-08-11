# Node Spec — Fitness & Training

> Canonical. Fitness is a social training node and is deliberately separate from the sensitive
> medical Health node (D24). Global rules from `00_README_and_Changelog.md` apply.

## 1. Purpose and boundary

Fitness helps household members plan and log strength, running, swimming, cycling and other
cardio. It owns exercises, training programs, live workout sessions and personal records.
It does **not** own medication, injuries, diagnoses, medical notes, body measurements, calories,
GPS routes or other medical/sensitive Health data.

## 2. Vocabulary

A **program** (or training plan) contains ordered **workouts** such as Day 1, Day 2 and Day 3.
A workout contains prescribed exercises and target sets/reps/weight/time/distance. A completed
**session** is an immutable snapshot of what the person actually did.

## 3. Exercise library

Exercises have a name, activity type, target muscle group, measurement mode and units.
Measurement modes are `reps_weight`, `reps_only`, `duration` and `distance_time`. The database is
seeded with common strength, running, swimming, cycling, cardio and mobility exercises. Users can
search/filter and add exercises; referenced exercises are archived rather than destroyed.

## 4. Programs and assignment

Programs contain any number of ordered workout days and can be assigned to People (D12). Starting
a workout copies the prescription into session rows. Editing the program later never changes
history. Managers can assign and log for anyone; ordinary users can manage only their own subject
profile.

## 4a. Weights default to last time

A prescribed weight goes stale the moment somebody progresses past it, so a new set opens at the
weight that person actually completed the previous time they trained that exercise. Defaults are
taken set for set from the most recent completed session containing the exercise: set three opens
at last session's set three, and any set beyond the number performed last time repeats the final
one. A program target weight is used only until the exercise has history, and reps stay with the
program's prescription unless it gives none. Adding an exercise mid-workout prefills the same way;
adding a set repeats the set just done in the current workout. Only completed sets of finished
sessions count, so abandoned training never becomes the default. The history is
visibility-filtered, so another person's private session never prefills or is named on screen.
The live session reports the training each default came from, keeping the number explainable.

## 5. Live session

An active session records its start time and exposes large touch controls. Each set may record
reps, weight, duration and/or distance. Sets can be completed/uncompleted. Exercises and sets may
be added during training and exercises may be dropped, preserving the actual session rather than
rewriting its source program. Finishing stores elapsed duration, total reps and strength volume.

## 6. Personal records

Finishing a session compares completed sets with current records. Strength records include
heaviest weight, most reps and Epley estimated one-rep max (for sets of 12 reps or fewer).
Distance activities track longest distance and fastest time for each exact distance, supporting
records such as 1 km and 5 km runs and standard swim distances. Current records link to the
source session and set.

## 7. Visibility, social activity and notifications

Programs and sessions default to household visibility and may be private. Household-visible
completed sessions and records appear in permitted history and the recent-training Hub widget.
Other users with `fitness.view` receive an in-app notification when a household-visible session
finishes, including the count of new personal records. Private sessions create no social
notification. Fitness Corner activity and its notification deep-link to that immutable completed
session. An authorised viewer can expand a compact snapshot of duration, exercises and completed
sets/reps/weight/time/distance without entering the full Fitness workspace; the detail is resolved
live so a later privacy change immediately removes access. Fitness is unavailable on kiosk
initially; child accounts are read-only by default.

## 8. API and layering

Routes live under `/api/v1/fitness/`: exercises, programs, sessions, live exercise/set actions,
finish/abandon and records. Models inherit `HouseholdBaseModel`; views are thin; writes use
services; reads use visibility-filtered selectors; lifecycle events publish through D4 signals.

## 9. V1 completion and follow-ups

V1 is complete when the responsive web app supports the exercise → program → assignment → live
session → history/records loop, sharing/privacy, notifications, seeded data and tests. Useful
follow-ups: reusable supersets/circuits, rest timer alerts, RPE/RIR, warm-up sets, pace splits,
weekly schedule/calendar planning, goals and trends, exercise aliases/equipment, CSV export and
optional integrations with wearables. None should move medical data into this node.
