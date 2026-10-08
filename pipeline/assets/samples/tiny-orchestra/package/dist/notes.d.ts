import type { ScoreNote } from './types.ts';
/**
 * MIDI number of a note name in scientific pitch notation: `"C4"` = 60,
 * `"F#3"`, `"Bb5"`, `"C-1"` = 0. Sharps `#`/`♯`/`x` (double), flats
 * `b`/`♭`. NaN for anything else.
 */
export declare function noteToMidi(name: string): number;
/** Note name of a MIDI number, with sharps: 60 -> `"C4"`, 61 -> `"C#4"`. */
export declare function midiToNote(midi: number): string;
/** A pitch as a score may give it: MIDI number, note name, or null (unpitched). */
export declare function toMidi(pitch: number | string | null | undefined): number | null;
export interface SequenceOptions {
    /** Beat of the first note. Default 0. */
    start?: number;
    /** Length of a note that gives none, until one does. Default 1. */
    length?: number;
}
/**
 * Notes of a part written as text, one token after the other:
 *
 *     sequence('C4 D4 E4:2 | G4+B4+D5:4 r:1 x:0.5@0.9')
 *
 * - `C4`, `F#3`, `Bb5` - a note (or a MIDI number, `60`)
 * - `C4+E4+G4` - a chord
 * - `x` - an unpitched hit, `x.soft` with a variant
 * - `r` - a rest
 * - `:2` - length in beats; it carries over to the following tokens
 * - `@0.8` - velocity of this token
 * - `|` - a bar line, ignored (only for reading)
 *
 * Throws on a token it does not understand - the text is written by hand
 * and a typo should not go unnoticed.
 */
export declare function sequence(text: string, { start, length }?: SequenceOptions): ScoreNote[];
//# sourceMappingURL=notes.d.ts.map