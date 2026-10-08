import type { InstrumentName } from './instruments.ts';
import type { TempoChange } from './tempo.ts';
import type { Score } from './types.ts';
/** One note of a MIDI file, times in beats (quarter notes). */
export interface MidiNote {
    /** Index of the track chunk. */
    track: number;
    /** 0..15; 9 is the General MIDI percussion channel ("channel 10"). */
    channel: number;
    /** Program (0..127) of the channel when the note starts. Default 0. */
    program: number;
    /** MIDI key; for percussion, the drum sound. */
    midi: number;
    /** 0..1, key velocity / 127. */
    velocity: number;
    beat: number;
    length: number;
}
export interface MidiTrack {
    /** First track name (meta event 0x03). */
    name: string | undefined;
}
/** What `parseMidi` finds in a file. */
export interface MidiData {
    format: 0 | 1;
    ticksPerBeat: number;
    /** Tempo changes, sorted; the first one is at beat 0 and gives the start tempo (default 120). */
    tempo: TempoChange[];
    /** First time signature as `[numerator, denominator]`. Default `[4, 4]`. */
    timeSignature: [number, number];
    /** Quarter notes per bar of the first time signature: 6/8 -> 3. */
    beatsPerBar: number;
    /** Beat of the last event of any track. */
    lengthBeats: number;
    tracks: MidiTrack[];
    /** All notes, sorted by beat, then track. */
    notes: MidiNote[];
}
/**
 * Parse a Standard MIDI File (format 0 or 1, ticks-per-quarter division).
 * Note on with velocity 0 counts as note off; on/off of the same key on the
 * same channel of a track pair first in, first out, and notes still held end
 * with their track. Sysex and all other events are skipped. Throws on SMPTE
 * division, format 2 and malformed or truncated data.
 */
export declare function parseMidi(data: ArrayBuffer | Uint8Array): MidiData;
/** A group of notes of one track, channel and program, to map to one instrument. */
export interface MidiGroup {
    track: number;
    trackName: string | undefined;
    channel: number;
    program: number;
    notes: readonly MidiNote[];
}
/** Where a percussion key goes: an unpitched instrument and its variant. */
export interface DrumHit<I extends string = InstrumentName> {
    instrument: I;
    variant?: string | undefined;
}
export interface MidiToScoreOptions<I extends string = InstrumentName> {
    /**
     * Instrument for a group of pitched notes (one track, channel and program),
     * or null to drop the group. Default `gmInstrument`.
     */
    instrument?: ((group: MidiGroup) => I | null) | undefined;
    /**
     * Instrument and variant for a note on the percussion channel (index 9),
     * by key, or null to drop it. Drum notes of all tracks become one part per
     * instrument. `false`: channel 9 is an ordinary channel for `instrument`.
     * Default `gmDrum`.
     */
    drums?: ((key: number, note: MidiNote) => DrumHit<I> | null) | false | undefined;
}
/**
 * Bundled instrument for a General MIDI program. Ensembles (strings, choir,
 * pads, organs -> strings; brass section -> brass; saxophones -> winds) and
 * pizzicato pick the family member by the group's median pitch; pianos,
 * guitars and anything without a closer match play on the harp.
 */
export declare function gmInstrument(group: MidiGroup): InstrumentName;
/** Bundled instrument for a General MIDI percussion key; null for keys without one (hi-hats, toms, ...). */
export declare function gmDrum(key: number): DrumHit | null;
/**
 * A score from a parsed MIDI file. Pitched notes are grouped by track,
 * channel and program, and each group becomes a part of the instrument
 * `options.instrument` names for it; percussion (channel index 9) becomes
 * one part per instrument that `options.drums` maps its keys to, with the
 * variant on every note. Parts are named after their track, else their
 * instrument (made unique with " 2", " 3", ...). The length is rounded up
 * to whole bars.
 *
 * The defaults map to the bundled instruments; with other instrument names,
 * pass both `instrument` and `drums` (or `drums: false`).
 */
export declare function midiToScore<I extends string = InstrumentName>(data: MidiData, options?: MidiToScoreOptions<I>): Score<I>;
//# sourceMappingURL=midi.d.ts.map