"""Small, dependency-free Standard MIDI File reader.

``read_midi(path)`` returns ``format``, ``ticks_per_quarter``, ``tracks`` and
``tempos``. Each track has a name, notes as
``[start_quarter, end_quarter, pitch, velocity, channel]``, an end position,
tempo changes, sustain-pedal messages, and an overlapping-note-on count.
Channels are zero-based. Tempo entries contain ``quarter`` and
``microseconds_per_quarter``; the file-level entries also identify the track.
No tempo conversion is needed for the returned quarter-note positions.

Durations describe key-down intervals. Sustain (CC64) is recorded but NOT
applied: callers requiring pedal-free material must check ``sustain_pedal``.
Repeated note-ons on a channel/pitch are paired FIFO with successive note-offs;
MIDI has no voice identifier to resolve that ambiguity. This convention and
the overlap count are explicit rather than silently overwriting active notes.
Format 2 tracks have independent timelines and must not be merged as voices.
No musical files are opened by the module's in-memory self-checks.
"""

from collections import deque
from pathlib import Path
import struct


class MidiError(ValueError):
    """Malformed or unsupported MIDI input."""


class _Reader:
    def __init__(self, data, label):
        self.data = memoryview(data)
        self.position = 0
        self.label = label

    @property
    def remaining(self):
        return len(self.data) - self.position

    def fail(self, message):
        raise MidiError(f"{self.label}, byte {self.position}: {message}")

    def take(self, count):
        if count < 0 or count > self.remaining:
            self.fail(f"truncated input: need {count}, have {self.remaining}")
        result = self.data[self.position:self.position + count]
        self.position += count
        return result

    def byte(self):
        return self.take(1)[0]

    def vlq(self):
        value = 0
        for _ in range(4):
            part = self.byte()
            value = (value << 7) | (part & 0x7F)
            if part < 0x80:
                return value
        self.fail("variable-length quantity exceeds four bytes")


def _text(payload):
    raw = bytes(payload)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def _track(data, ticks_per_quarter, index):
    reader = _Reader(data, f"track {index}")
    result = {"name": "", "notes": [], "tempos": [], "sustain_pedal": [],
              "overlapping_note_ons": 0}
    active = {}
    tick = 0
    running = None
    ended = False
    while reader.remaining:
        tick += reader.vlq()
        lead = reader.byte()
        first_data = None
        if lead < 0x80:
            if running is None:
                reader.fail("data byte without running channel status")
            status = running
            first_data = lead
        else:
            status = lead

        quarter = tick / ticks_per_quarter
        if 0x80 <= status <= 0xEF:
            running = status
            kind, channel = status & 0xF0, status & 0x0F
            count = 1 if kind in (0xC0, 0xD0) else 2
            values = [] if first_data is None else [first_data]
            values.extend(reader.take(count - len(values)))
            if any(value >= 0x80 for value in values):
                reader.fail("status byte where channel-event data was required")
            if kind in (0x80, 0x90):
                pitch, velocity = values
                key = (channel, pitch)
                if kind == 0x90 and velocity:
                    queue = active.setdefault(key, deque())
                    if queue:
                        result["overlapping_note_ons"] += 1
                    queue.append((tick, velocity))
                else:
                    queue = active.get(key)
                    if not queue:
                        reader.fail(f"unmatched note-off: channel {channel}, pitch {pitch}")
                    start, onset_velocity = queue.popleft()
                    result["notes"].append(
                        [start / ticks_per_quarter, quarter, pitch,
                         onset_velocity, channel])
                    if not queue:
                        del active[key]
            elif kind == 0xB0 and values[0] == 64:
                result["sustain_pedal"].append(
                    {"quarter": quarter, "channel": channel, "value": values[1]})
        elif status == 0xFF:
            running = None
            meta_type = reader.byte()
            if meta_type >= 0x80:
                reader.fail("invalid meta-event type")
            payload = reader.take(reader.vlq())
            if meta_type == 0x03:
                result["name"] = _text(payload)
            elif meta_type == 0x51:
                if len(payload) != 3:
                    reader.fail("tempo event must contain exactly three bytes")
                tempo = int.from_bytes(payload, "big")
                if not tempo:
                    reader.fail("tempo must be positive")
                result["tempos"].append(
                    {"quarter": quarter, "microseconds_per_quarter": tempo})
            elif meta_type == 0x2F:
                if payload:
                    reader.fail("end-of-track event must have zero length")
                if reader.remaining:
                    reader.fail("bytes remain after end-of-track")
                if active:
                    reader.fail("end-of-track with unclosed notes")
                ended = True
                break
        elif status in (0xF0, 0xF7):
            running = None
            reader.take(reader.vlq())
        else:
            reader.fail(f"unsupported system status 0x{status:02x} in MIDI file")
    if not ended:
        reader.fail("missing end-of-track event")
    result["end_quarter"] = tick / ticks_per_quarter
    result["notes"].sort(key=lambda n: (n[0], n[4], n[2], n[1]))
    return result


def _parse_midi(data):
    reader = _Reader(data, "MIDI file")
    if bytes(reader.take(4)) != b"MThd":
        reader.fail("expected MThd header")
    header_size = int.from_bytes(reader.take(4), "big")
    if header_size < 6:
        reader.fail("MThd header shorter than six bytes")
    header = reader.take(header_size)
    midi_format, count, division = struct.unpack(">HHH", header[:6])
    if midi_format not in (0, 1, 2):
        reader.fail(f"unsupported MIDI format {midi_format}")
    if count == 0 or (midi_format == 0 and count != 1):
        reader.fail("invalid track count for MIDI format")
    if division & 0x8000:
        reader.fail("SMPTE time division is not supported")
    if division == 0:
        reader.fail("ticks per quarter must be positive")
    tracks = []
    for index in range(count):
        if bytes(reader.take(4)) != b"MTrk":
            reader.fail("expected MTrk chunk")
        size = int.from_bytes(reader.take(4), "big")
        tracks.append(_track(reader.take(size), division, index))
    if reader.remaining:
        reader.fail("unexpected bytes after declared tracks")
    tempos = [{**entry, "track": index}
              for index, track in enumerate(tracks) for entry in track["tempos"]]
    tempos.sort(key=lambda entry: (entry["quarter"], entry["track"]))
    return {"format": midi_format, "ticks_per_quarter": division,
            "tracks": tracks, "tempos": tempos}


def read_midi(path):
    """Read one SMF, rejecting truncation, SMPTE timing and unpaired notes."""
    return _parse_midi(Path(path).read_bytes())


if __name__ == "__main__":
    def fixture(track, division=480):
        return (b"MThd" + struct.pack(">IHHH", 6, 0, 1, division)
                + b"MTrk" + struct.pack(">I", len(track)) + track)

    # Includes two-byte VLQ delta, running status, overlapping same-pitch notes,
    # note-on/velocity-zero release, explicit note-off, meta and SysEx skipping.
    events = (
        b"\x00\xff\x03\x04Test"
        b"\x00\xff\x51\x03\x07\xa1\x20"
        b"\x00\xf0\x03\x01\x02\xf7"
        b"\x00\xc0\x05\x00\x06"  # program change with running status
        b"\x00\xd0\x20\x00\x21"  # channel pressure with running status
        b"\x00\x90\x3c\x64"
        b"\x78\x3c\x50"
        b"\x78\x3c\x00"
        b"\x81\x70\x80\x3c\x00"
        b"\x00\xb0\x40\x7f"
        b"\x00\xff\x01\x02\x80\xff"
        b"\x00\xff\x2f\x00")
    parsed = _parse_midi(fixture(events))
    assert parsed["ticks_per_quarter"] == 480
    track = parsed["tracks"][0]
    assert track["name"] == "Test"
    assert track["notes"] == [[0.0, 0.5, 60, 100, 0], [0.25, 1.0, 60, 80, 0]]
    assert track["overlapping_note_ons"] == 1
    assert track["tempos"] == [{"quarter": 0.0, "microseconds_per_quarter": 500000}]
    assert parsed["tempos"][0]["track"] == 0
    assert track["sustain_pedal"] == [{"quarter": 1.0, "channel": 0, "value": 127}]

    invalid = [
        fixture(events, 0xE728),                 # SMPTE
        fixture(events)[:-1],                  # chunk truncation
        fixture(b"\x81\x80\x80\x80\x00"),  # overlong VLQ
        fixture(b"\x00\x3c\x40"),            # no running status
        fixture(b"\x00\x90\x3c\xff"),      # invalid data byte
        fixture(b"\x00\x90\x3c\x40\x00\xff\x2f\x00"),  # dangling note
        fixture(b"\x00\x80\x3c\x00\x00\xff\x2f\x00"),  # unmatched off
        fixture(b"\x00\xff\x2f\x00\x00"),  # bytes after EOT
        fixture(b"\x00\xff\x51\x02\x01\x02\x00\xff\x2f\x00"),
        fixture(b"\x00\xc0\x01\x00\xff\x01\x00\x00\x02"),
    ]
    for data in invalid:
        try:
            _parse_midi(data)
        except MidiError:
            pass
        else:
            raise AssertionError("invalid in-memory fixture was accepted")
    print("MIDI reader in-memory checks passed")
