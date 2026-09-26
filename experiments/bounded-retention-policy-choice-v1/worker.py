"""Arrived-observation retention worker; no score/archive/file/network access.

Protocol: contiguous completed one-second `unit` messages, each containing exact
events clipped to that unit and clipping flags. Optional `completed_support`
supplies an occurrence boundary AFTER its complete evidence has arrived. It must
fit in the actual four-unit ring. A final `predict` has no query label; optional
`remove_support` is a destructive evaluator intervention. JSON receipts are
streamed out and are never retained as a predictor-readable archive.
"""
from __future__ import annotations

import argparse
import builtins
from collections import deque
import hashlib
import io
import json
import math
import os
import random
import resource
import socket
import sys
import time

import numpy as np
from global_matcher import predict as frozen_predict

CAPACITY = 8
BYTE_CAP = 256 * 1024
CEILING_CAPACITY = 512
CEILING_BYTE_CAP = 8 * 1024 * 1024
SEED = 202609260701


def deep_bytes(value, seen=None):
    seen = set() if seen is None else seen
    if id(value) in seen:
        return 0
    seen.add(id(value))
    n = sys.getsizeof(value)
    if isinstance(value, np.ndarray) and not value.flags.owndata:
        # Views otherwise report only their header; count referenced bytes too.
        n += value.nbytes
    if isinstance(value, dict):
        n += sum(deep_bytes(k, seen) + deep_bytes(v, seen) for k, v in value.items())
    elif isinstance(value, (tuple, list, deque)):
        n += sum(deep_bytes(v, seen) for v in value)
    # Owning ndarray.__sizeof__ includes data; views conservatively count it above.
    return n


def digest(events, support):
    h = hashlib.sha256()
    h.update(np.asarray(events, dtype='<f8').tobytes())
    h.update(np.asarray(support, dtype='<f8').tobytes())
    return h.hexdigest()


def descriptor(events):
    """Fixed35 coordinates:11 signed intervals/12;24 normalized endpoints.

    Missing notes/nonfinite/nonmonophonic records are malformed, not imputed.
    Constant-pitch records are valid: all11 pitch components are exactly zero.
    Endpoint normalization uses positive last-offset minus first-onset span.
    """
    if events.shape != (12, 3) or not np.isfinite(events).all():
        raise ValueError('complete occurrence requires12 finite events')
    if (np.any(events[:, 1] <= events[:, 0]) or
            np.any(events[1:, 0] < events[:-1, 1]) or
            np.any(events[:, 2] != np.floor(events[:, 2])) or
            np.any(events[:, 2] < 0) or np.any(events[:, 2] > 127)):
        raise ValueError('malformed complete monophonic occurrence')
    span = float(events[-1, 1] - events[0, 0])
    if span <= 0:
        raise ValueError('nonpositive occurrence span')
    return np.concatenate((np.diff(events[:, 2]) / 12.0,
                           ((events[:, :2] - events[0, 0]) / span).ravel()))


def distance(a, b):
    return float(np.mean((a[:11] - b[:11]) ** 2) +
                 np.mean((a[11:] - b[11:]) ** 2))


def joined_events(units):
    events, left, right = [], [], []
    for unit in units:
        for event, lclip, rclip in zip(unit['events'], unit['left'], unit['right']):
            if (events and right[-1] and lclip and
                    events[-1][1] == event[0] and events[-1][2] == event[2]):
                events[-1][1] = float(event[1])
                right[-1] = bool(rclip)
            else:
                events.append(event.tolist())
                left.append(bool(lclip))
                right.append(bool(rclip))
    return (np.asarray(events, dtype=float).reshape(-1, 3),
            np.asarray(left, dtype=bool), np.asarray(right, dtype=bool))


def install_guard():
    def denied(*args, **kwargs):
        raise PermissionError('predictor file/network access disabled')
    builtins.open = denied
    io.open = denied
    os.open = denied
    socket.socket = denied


class Worker:
    def __init__(self, policy, seed):
        self.policy = policy
        self.seed = seed
        self.rng = random.Random(seed) if policy == 'reservoir' else None
        self.records = []
        self.recent = deque()
        self.last_unit = -1
        self.seen_occurrences = 0
        self.replacements = 0
        self.admission_rejections = 0
        self.recent_evictions = 0
        self.peak_bytes = 0
        self.peak_policy_scratch_bytes = 0
        self.last_construction_scratch_bytes = 0
        self.capacity = CEILING_CAPACITY if policy == 'unpressured' else CAPACITY
        self.byte_cap = CEILING_BYTE_CAP if policy == 'unpressured' else BYTE_CAP

    def storage(self):
        # Conservatively count the recent ring inside the byte cap too.
        value = [self.__dict__, None if self.rng is None else self.rng.getstate()]
        total = deep_bytes(value)
        self.peak_bytes = max(self.peak_bytes, total)
        if len(self.records) > self.capacity or total > self.byte_cap:
            raise ValueError('persistent capacity exceeded')
        return total

    def admit(self, events, support):
        self.seen_occurrences += 1
        record = {'id': self.seen_occurrences, 'events': events.copy(),
                  'support': tuple(support), 'descriptor': descriptor(events),
                  'hash': digest(events, support), 'available_at': self.last_unit + 1}
        self.peak_policy_scratch_bytes = max(self.peak_policy_scratch_bytes, deep_bytes(record))
        result = {'arrived_id': record['id'], 'events_sha256': record['hash'],
                  'support': list(support), 'rng_draw': None,
                  'evicted_id': None, 'admitted': False, 'incoming_discarded': False}
        if self.policy == 'present':
            result['incoming_discarded'] = True
            self.admission_rejections += 1
            return result
        if len(self.records) < self.capacity:
            self.records.append(record)
            result['admitted'] = True
            return result
        if self.policy == 'unpressured':
            raise ValueError('unpressured declared record capacity exceeded')
        if self.policy == 'fifo':
            index = 0
        elif self.policy == 'reservoir':
            index = self.rng.randrange(self.seen_occurrences)
            result['rng_draw'] = {'population_size': self.seen_occurrences,
                                  'inclusive_lower': 0,
                                  'exclusive_upper': self.seen_occurrences,
                                  'draw': index}
            if index >= self.capacity:
                self.admission_rejections += 1
                result['incoming_discarded'] = True
                return result
        elif self.policy == 'diversity':
            nine = self.records + [record]
            matrix = [[distance(a['descriptor'], b['descriptor']) for b in nine]
                      for a in nine]
            self.peak_policy_scratch_bytes = max(self.peak_policy_scratch_bytes,
                                                 deep_bytes([nine, matrix]))
            scores = []
            for omitted in range(9):
                survivors = [i for i in range(9) if i != omitted]
                minimum = min(matrix[i][j] for i in survivors for j in survivors if i < j)
                scores.append(minimum)
            # Binary64 arithmetic and exact equality; no learned epsilon/tolerance.
            best = max(scores)
            index = min((i for i, score in enumerate(scores) if score == best),
                        key=lambda i: (nine[i]['id'], nine[i]['hash']))
            result['diversity_removal_scores'] = scores
            if index == 8:
                self.admission_rejections += 1
                result['incoming_discarded'] = True
                return result
        else:
            raise ValueError('unknown policy')
        result.update(evicted_id=self.records[index]['id'], admitted=True)
        if self.policy == 'fifo':
            self.records.pop(index)
            self.records.append(record)
        else:
            self.records[index] = record
        self.replacements += 1
        return result

    def arrive(self, command):
        allowed = {'op', 'unit', 'events', 'event_left_clipped',
                   'event_right_clipped', 'completed_support', 'available_at'}
        if set(command) - allowed:
            raise ValueError('unexpected arrival metadata')
        u = command['unit']
        if type(u) is not int or u != self.last_unit + 1:
            raise ValueError('units must arrive once in contiguous order from zero')
        if command.get('available_at', u + 1) != u + 1:
            raise ValueError('unit evidence is unavailable before completed unit end')
        events = np.asarray(command['events'], dtype=float).reshape(-1, 3).copy()
        if any(type(v) is not bool for key in ('event_left_clipped', 'event_right_clipped')
               for v in command[key]):
            raise ValueError('clipping flags must be boolean observations')
        left = np.asarray(command['event_left_clipped'], dtype=bool).copy()
        right = np.asarray(command['event_right_clipped'], dtype=bool).copy()
        if left.shape != (len(events),) or right.shape != left.shape:
            raise ValueError('event clipping flags missing/misaligned')
        if (not np.isfinite(events).all() or np.any(events[:, 0] < u) or
                np.any(events[:, 1] > u + 1) or np.any(events[:, 1] <= events[:, 0]) or
                np.any(events[1:, 0] < events[:-1, 1]) or
                np.any(events[:, 2] != np.floor(events[:, 2])) or
                np.any(events[:, 2] < 0) or np.any(events[:, 2] > 127)):
            raise ValueError('invalid arrived event packet')
        if np.any(left & (events[:, 0] != u)) or np.any(right & (events[:, 1] != u + 1)):
            raise ValueError('clipping flags must lie on arrival boundaries')
        self.last_unit = u
        self.recent.append({'unit': u, 'events': events, 'left': left, 'right': right})
        evicted_units = []
        while self.recent and self.recent[0]['unit'] < u - 3:
            evicted_units.append(self.recent.popleft()['unit'])
            self.recent_evictions += 1
        completion = None
        support = command.get('completed_support')
        if support is not None:
            if (len(support) != 2 or any(type(v) not in (int, float) for v in support) or
                    not all(math.isfinite(v) and v == int(v) for v in support)):
                raise ValueError('occurrence support must use integer unit boundaries')
            lo, hi = map(int, support)
            if lo < u - 3 or hi != u + 1 or hi <= lo:
                raise ValueError('completion must be newly available inside recent ring')
            chosen = [r for r in self.recent if lo <= r['unit'] < hi]
            if [r['unit'] for r in chosen] != list(range(lo, hi)):
                raise ValueError('complete support is absent from recent observations')
            complete, lc, rc = joined_events(chosen)
            if np.any(lc) or np.any(rc):
                raise ValueError('claimed complete occurrence has censored events')
            completion = self.admit(complete, [lo, hi])
        return {'type': 'arrival', 'unit': u, 'available_at': u + 1,
                'received_monotonic': time.monotonic(),
                'unit_events_sha256': digest(events, [u, u + 1]),
                'completion': completion, 'recent_units': [r['unit'] for r in self.recent],
                'recent_evicted_units': evicted_units,
                'recent_evictions': self.recent_evictions,
                'retained_ids': [r['id'] for r in self.records],
                'persistent_replacements': self.replacements,
                'admission_rejections': self.admission_rejections,
                'persistent_bytes': self.storage(), 'persistent_capacity': self.capacity,
                'persistent_byte_cap': self.byte_cap}

    def remove(self, support):
        if len(support) != 2 or not all(math.isfinite(float(x)) for x in support):
            raise ValueError('invalid removal support')
        lo, hi = map(float, support)
        if lo >= hi:
            raise ValueError('invalid removal support')
        removed = [r['id'] for r in self.records if r['support'][0] < hi and lo < r['support'][1]]
        self.records = [{**r, 'events': r['events'].copy(),
                         'descriptor': descriptor(r['events'])}
                        for r in self.records if r['id'] not in removed]
        # Delete whole intersecting units, conservatively removing all derived edges.
        self.recent = deque(r for r in self.recent if not (r['unit'] < hi and lo < r['unit'] + 1))
        return removed

    def observation_state(self):
        # Materialize per-unit evidence only from surviving records and recent data.
        units = {}
        for record in self.records:
            for u in range(int(record['support'][0]), int(record['support'][1])):
                events, lc, rc = [], [], []
                for on, off, pitch in record['events']:
                    if on < u + 1 and off > u:
                        events.append([max(on, u), min(off, u + 1), pitch])
                        lc.append(on < u)
                        rc.append(off > u + 1)
                units[u] = {'unit': u, 'events': np.asarray(events, dtype=float).reshape(-1, 3),
                            'left': np.asarray(lc, dtype=bool), 'right': np.asarray(rc, dtype=bool)}
        for packet in self.recent:
            u = packet['unit']
            if u in units and not np.array_equal(units[u]['events'], packet['events']):
                raise ValueError('retained and recent observations disagree')
            units[u] = packet
        ordered = [units[u] for u in sorted(units)]
        timestamps = np.concatenate([r['unit'] + np.arange(10) * .1 + .05 for r in ordered]) if ordered else np.empty(0)
        unit_ids = np.repeat([r['unit'] for r in ordered], 10)
        events, lc, rc = joined_events(ordered)
        segments = []
        for r in ordered:
            u = r['unit']
            if segments and segments[-1][1] == u:
                segments[-1][1] = u + 1
            else:
                segments.append([u, u + 1])
        labels = np.full(len(timestamps), 128, dtype=int)
        for on, off, pitch in events:
            labels[(timestamps >= on) & (timestamps < off)] = int(pitch)
        clean = np.zeros((len(timestamps), 129), dtype=np.float64)
        clean[np.arange(len(timestamps)), labels] = 1
        state = {'t': timestamps, 'unit': unit_ids, 'rms': (labels != 128).astype(float),
                'clean': clean, 'available_at': unit_ids + 1,
                'events': events, 'segments': np.asarray(segments, dtype=float).reshape(-1, 2),
                'event_left_clipped': lc, 'event_right_clipped': rc}
        self.last_construction_scratch_bytes = deep_bytes([state, units, ordered, labels])
        return state

    def answer(self):
        processing_started = time.monotonic()
        state = self.observation_state()
        stored = self.storage()
        scratch = deep_bytes(state)
        began = time.monotonic()
        result = frozen_predict(state, exact=True)
        finished = time.monotonic()
        mapped = []
        for index, candidate in enumerate(result['candidates']):
            containing = [r['id'] for r in self.records
                          if r['support'][0] <= candidate['start'] and candidate['end'] <= r['support'][1]]
            intersecting = [r['id'] for r in self.records
                            if r['support'][0] < candidate['end'] and candidate['start'] < r['support'][1]]
            mapped.append({'candidate_index': index, 'containing_record_ids': containing,
                           'intersecting_record_ids': intersecting})
        recent_events, _, _ = joined_events(self.recent)
        recent_support = [[r['unit'], r['unit'] + 1] for r in self.recent]
        selected_record_id = None
        if result['accepted'] and len(mapped) == 1 and len(mapped[0]['containing_record_ids']) == 1:
            selected_record_id = mapped[0]['containing_record_ids'][0]
        output = {**result, 'type': 'prediction', 'policy': self.policy, 'raw': result,
                'candidate_record_mappings': mapped,
                'candidate_record_ids': [m['containing_record_ids'] for m in mapped],
                'selected_record_id': selected_record_id,
                'compatible_record_ids': sorted({i for m in mapped for i in m['containing_record_ids']}),
                'retained_records': [{'id': r['id'], 'support': list(r['support']),
                                      'events': r['events'].tolist(),
                                      'descriptor': r['descriptor'].tolist(),
                                      'hash': r['hash'], 'events_sha256': r['hash'],
                                      'available_at': r['available_at']}
                                     for r in self.records],
                'recent_units': [r['unit'] for r in self.recent],
                'ring_events_sha256': digest(recent_events, recent_support),
                'replacements': self.replacements,
                'persistent_replacements': self.replacements,
                'admission_rejections': self.admission_rejections,
                'recent_evictions': self.recent_evictions,
                'persistent_bytes': stored, 'peak_persistent_bytes': self.peak_bytes,
                'scratch_input_bytes': scratch, 'scratch_output_bytes': deep_bytes(result),
                'scratch_construction_bytes': self.last_construction_scratch_bytes,
                'peak_policy_scratch_bytes': self.peak_policy_scratch_bytes,
                'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                'compute_seconds': finished - began,
                'prediction_finished_monotonic': finished,
                'simulation_observations_available_at': self.last_unit + 1,
                'simulation_compute_only_finish': self.last_unit + 1 + finished - began,
                'input_events_sha256': digest(state['events'], state['segments']),
                'query_and_history_rule': 'unchanged frozen G-exact; no query identity supplied'}
        ready = time.monotonic()
        output.update(output_ready_monotonic=ready,
                      processing_seconds=ready - processing_started,
                      output_available_at=self.last_unit + 1 + ready - processing_started,
                      output_availability_semantics='completed-unit time plus local processing; broker records actual receipt')
        return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('policy', choices=['fifo', 'reservoir', 'diversity', 'unpressured', 'present'])
    parser.add_argument('--seed', type=int, default=SEED)
    args = parser.parse_args()
    worker = Worker(args.policy, args.seed)
    install_guard()
    print(json.dumps({'type': 'ready', 'ready': True, 'policy': args.policy, 'seed': args.seed,
                      'guard': True, 'rng': 'Python random.Random Algorithm R randrange(n)',
                      'supplied_occurrence_segmentation': True}), flush=True)
    for line in sys.stdin:
        command = json.loads(line)
        if command['op'] == 'unit':
            result = worker.arrive(command)
            print(json.dumps(result, allow_nan=False), flush=True)
            del command, line, result
        elif command['op'] == 'predict':
            if set(command) - {'op', 'remove_support'}:
                raise ValueError('unexpected readout metadata')
            removal_requested = command.get('remove_support') is not None
            removed = worker.remove(command['remove_support']) if removal_requested else []
            # Eliminate evaluator removal coordinates before candidate evaluation.
            del command, line
            result = worker.answer()
            result['removed_record_ids'] = removed
            result['source_removed'] = removal_requested
            print(json.dumps(result, allow_nan=False), flush=True)
            return
        else:
            raise ValueError('unknown operation')


if __name__ == '__main__':
    main()
