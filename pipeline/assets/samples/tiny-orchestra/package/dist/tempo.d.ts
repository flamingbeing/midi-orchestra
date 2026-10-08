/**
 * A tempo change: from `beat` on the tempo is `bpm`. With `ramp`, the tempo
 * moves there gradually from the previous change instead (a ritardando or
 * accelerando that arrives at `bpm` on `beat`).
 */
export type TempoChange = [beat: number, bpm: number, ramp?: boolean | undefined];
/** Seconds since beat 0 of a score, and back. */
export interface TempoMap {
    /** Seconds from beat 0 to `beat` (negative before beat 0). */
    seconds(beat: number): number;
    /** Inverse of `seconds`. */
    beatAt(seconds: number): number;
    /** Tempo at `beat`. */
    bpmAt(beat: number): number;
}
/**
 * Tempo map from a base tempo and a list of changes. Changes before beat 0
 * or with an invalid tempo are ignored; the base tempo holds until the first
 * change (and before beat 0).
 */
export declare function tempoMap(bpm: number, changes?: readonly TempoChange[]): TempoMap;
/**
 * A tempo map that repeats every `lengthBeats` - for loops, where each pass
 * starts again at the tempo of beat 0.
 */
export declare function repeating(map: TempoMap, lengthBeats: number): TempoMap;
/** Clock time <-> beat for one performance. */
export interface Timeline {
    /** Clock time at which `beat` sounds. */
    time(beat: number): number;
    /** Beat at clock time `time`. */
    beat(time: number): number;
}
/**
 * The timeline of a performance: `startBeat` sounds at `startTime`, and the
 * score's tempo map is played `factor` times as fast. `setFactor` changes
 * the speed from a given beat on, without moving anything before it.
 */
export declare class LiveTimeline implements Timeline {
    private readonly map;
    private readonly anchors;
    constructor(map: TempoMap, startTime: number, startBeat?: number, factor?: number);
    /** Current speed factor (of the last change). */
    get factor(): number;
    time(beat: number): number;
    beat(time: number): number;
    /** Tempo (bpm) at `beat`, including the factor. */
    bpmAt(beat: number): number;
    /** From `beat` on, play `factor` times as fast as the tempo map. */
    setFactor(factor: number, beat: number): void;
    private find;
}
//# sourceMappingURL=tempo.d.ts.map