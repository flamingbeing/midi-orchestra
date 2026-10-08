import type { DynamicsPoint, Part, Score } from './types.ts';
export declare const beatToTime: (beat: number, startTime: number, bpm: number) => number;
export declare const timeToBeat: (time: number, startTime: number, bpm: number) => number;
/** A note of a score with part and call settings already applied. */
export interface ScoreEvent {
    beat: number;
    /** Index of the part in the score. */
    part: number;
    /** In beats. */
    length: number;
    instrument: string;
    midi: number | null;
    velocity: number;
    pan: number;
    variant: string | undefined;
}
/** What `scoreLength` needs of a score. */
export type ScoreShape = Pick<Score<string>, 'beatsPerBar' | 'lengthBeats'> & {
    parts?: readonly Pick<Part<string>, 'notes'>[];
};
/** Length of a score in beats: as given, or rounded up to whole bars. */
export declare function scoreLength(score: ScoreShape): number;
export interface FlattenOptions {
    /** Semitones added to every pitched note. */
    transpose?: number;
    /** Multiplies every velocity. */
    velocity?: number;
}
/**
 * Score -> flat event list sorted by beat. Transposition and level of the
 * part and of the call are applied here already, so that the scheduler only
 * has to read off events while the music is running.
 */
export declare function flattenScore(score: Pick<Score<string>, 'parts'>, { transpose, velocity }?: FlattenOptions): ScoreEvent[];
/** An event together with the absolute beat it sounds on. */
export interface Occurrence<E extends {
    beat: number;
} = ScoreEvent> {
    ev: E;
    beat: number;
}
/**
 * All events with a beat in [from, to). When looping, the score repeats every
 * `lengthBeats`; `beat` in the result is then the absolute beat since the
 * start (including the passes before).
 */
export declare function collectEvents<E extends {
    beat: number;
}>(events: readonly E[], lengthBeats: number, loop: boolean, from: number, to: number): Occurrence<E>[];
/** Position in beats for display: never negative, wrapped when looping. */
export declare function wrapPosition(beats: number, lengthBeats: number, loop: boolean): number;
/**
 * Next bar line at or after `beat`. Bars start on multiples of
 * `beatsPerBar`; when looping, every pass starts a new bar (even if the
 * length is not a whole number of bars). Without a loop, the end is the last
 * bar line.
 */
export declare function nextBarBeat(beat: number, beatsPerBar: number, lengthBeats: number, loop: boolean): number;
/** Bar number of `beat` if it starts a bar (see `nextBarBeat`), otherwise null. */
export declare function barAt(beat: number, beatsPerBar: number, lengthBeats: number, loop: boolean): number | null;
/**
 * One point of a part's dynamics, flattened for the scheduler. A ramp is
 * planned together with the point it starts from - so a ramp to the very end
 * of the score (which is never planned as a beat of its own) still happens.
 */
export interface DynamicsCue {
    beat: number;
    part: number;
    /** Gain (the level squared). */
    gain: number;
    /** The next point, if the part ramps there from this one. */
    rampTo: {
        beat: number;
        gain: number;
    } | null;
}
/** All dynamics of a score as cues sorted by beat. */
export declare function flattenDynamics(score: Pick<Score<string>, 'parts'>): DynamicsCue[];
/**
 * Gain of a part's dynamics at `beat` (within one pass; 1 without
 * dynamics), and the ramp it is in the middle of, if any - where a
 * performance that starts at `beat` picks up.
 */
export declare function dynamicsAt(points: readonly DynamicsPoint[] | undefined, beat: number): {
    gain: number;
    rampTo: DynamicsCue['rampTo'];
};
//# sourceMappingURL=score.d.ts.map