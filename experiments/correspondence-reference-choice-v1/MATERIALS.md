# Fixed development material

This generator produces clean score-derived observations. It performs no audio
rendering, acoustic extraction, MERT call, candidate call or outcome selection.
All eight families are development material. Construction labels stipulate an
earlier occurrence; they do not establish human perceptual identity.

`make_manifest()` records settings, acquisition provenance and original-file
hashes without parsing note events. `build_all(outputdir)` creates the forty
sessions once and refuses a nonempty destination. The parent worker owns its
invocation and preregistration. Code-writing and compilation do not generate or
expose this panel. There is no matcher import in this module.

## Sources and independent construction rules

Four Bach sources are BWV 773, 775, 778 and 781. Each uses note indices 24–35,
zero based, on the exact first nonempty track previously used for development.
Source-byte hashes, track identity and prior indices 0–11 are checked. The
selected events cannot overlap the earlier event range. Malformed, unavailable,
overlapping, pedal-dependent or out-of-range material aborts without selecting
another excerpt. These are new excerpts of previously exposed development
works, not unseen-work evidence.

Four novel motifs use seeds 202609260100–202609260103. Each is one twelve-event
diatonic random walk, with the frozen step, degree bound and duration distribution
in `materials.py`. No seed is tried twice. A complete signed-interval signature
collision with any twelve-event window of the eight PR18 **development**
unchanged-session histories aborts. Pairwise new source signatures must also be
distinct. This registry includes prior source, interference and query windows;
it does not read prior evaluation material or assert a search over all historical
Earworm studies or human/pretrained musical knowledge.

Within each stratum, sources start at 1.13, 1.30, 1.47 and 1.64 seconds. The
source span is linearly normalized to three seconds, preserving relative note
timings and gaps. The transposition cell uses respectively −5, −2, +2, +5
semitones. The stretch cell uses respectively 0.8, 1.25, 0.8, 1.25. Other cells
use zero shift and unit time scale. These are separate transformations.

Eight four-second intervening figures provide exactly 32 seconds between source
offset and return onset. Figures one through four cyclically rotate the source
pitch order by one through four events while scaling its timing from three to
four seconds. Figures five through eight are one-shot generated diatonic walks
from a separate deterministic generator seeded at family seed + 2,000,000.
Complete signatures must differ from the source and each other. A collision
aborts; there are no replacement attempts. Every earlier twelve-event window
is checked for an unintended complete source-equivalent ordered signature.
Short-fragment collisions are preserved, not excluded.

Each family has five sessions:

1. Unchanged return.
2. Transposed return.
3. Uniformly stretched return.
4. Pitch-inventory/rhythm foil: stably sort pitch positions, cyclically shift the
   sorted values by their maximum multiplicity, and restore the positions. This
   deterministic construction preserves the exact pitch multiset and all note
   timings but must change the interval sequence and an observed query row.
5. Near foil: increase one pitch by one semitone, choosing the last source event
   containing a sampled center in the fixed observed query. It must change an
   observed query row. The changed event and affected centers are retained only
   in evaluator labels. No skip path or matcher score chooses this event.

Both foils are checked for an unintended complete equivalent in earlier history.
Failure of any construction requirement preserves partial artifacts and a
`construction-failure.json` receipt. It does not launch a replacement family or
alternate generator. The eight separate diagnostic cases are owned by the
parent worker and are not generated here.

## Predictor input contract

Every session has `rows.npz`, `exact-events.npz` and `evaluatorlabels.json`.

`rows.npz` contains only:

- `t`: centers 0.05 + 0.1k seconds.
- `unit`: floor(t), the containing one-second arrival.
- `rms`: score-derived occupancy, exactly 0 or 1; this is not acoustic energy.
- `clean`: lossless float32 one-hot absolute MIDI pitch/silence rows, N×129.
- `available_at`: unit + 1 seconds.

The two equal-observation candidates receive the same rows and arrival history.
There are no IDs, source intervals, note boundaries, true shifts/scales or labels
inside that file. The final occupied center selects the last twenty query rows,
as in the historical query rule. The containing centers imply a two-second
query support from first center minus 50 ms to last center plus 50 ms. Label-side
records preserve these support endpoints; the candidates derive them from rows.

`exact-events.npz` is reserved for the separately labeled richer diagnostic. It
contains only `events`, ordered N×3 [onset, offset, MIDI pitch], and
`available_at`, the completed one-second unit containing each event offset. It
has no source labels or event IDs. The parent arrival adapter splits events
into unit-local arrived pieces, retaining explicit clipping flags and preventing
future offsets from becoming available early. This archive is a generation-side
file, not direct permission to give complete future events to a predictor.

`evaluatorlabels.json` separately records construction identity, full source and
query intervals, query sampled support, expected positive transformations, exact
source/query events, provenance, interference intervals and foil edit evidence.
The parent removes **whole one-second units overlapping the true source** for
the removal control, deletes associated records/caches, and re-derives indexes
without bridging the removed interval. Labels do not enter candidate search.

The saved archive manifest hashes every file. Validation should inspect these
saved arrays and hashes without regenerating the panel. The generator reports
construction time, file counts, and zero candidate readouts. The parent accounts
for arrival/storage/removal/retention behavior and overall resource limits.
