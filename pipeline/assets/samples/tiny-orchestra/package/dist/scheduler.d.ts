import { type ScoreEvent } from './score.ts';
import { type Timeline } from './tempo.ts';
import type { Voice } from './types.ts';
/** How far ahead notes are planned (seconds). */
export declare const LOOKAHEAD = 0.5;
/** Background tabs throttle setInterval to ~1 s, so plan further ahead there. */
export declare const LOOKAHEAD_HIDDEN = 2;
export declare const TICK_MS = 100;
export interface SchedulerOptions<C extends {
    beat: number;
} = {
    beat: number;
}> {
    events: readonly ScoreEvent[];
    lengthBeats: number;
    loop: boolean;
    /** Clock time <-> beat. Default: a constant `bpm` with beat `from` at `startTime`. */
    timeline?: Timeline | undefined;
    /** Clock time of beat `from`; only without a `timeline`. */
    startTime?: number | undefined;
    /** Only without a `timeline`. Default 120. */
    bpm?: number | undefined;
    /** Beat to start planning from. Default 0. */
    from?: number | undefined;
    /** Beat at which it ends (looping or not). Default: `lengthBeats`, or never when looping. */
    until?: number | undefined;
    /** Seconds to plan ahead, instead of LOOKAHEAD / LOOKAHEAD_HIDDEN. */
    lookahead?: number | undefined;
    /** The clock, usually `() => ctx.currentTime`. */
    now: () => number;
    /** Whether the page is in the background. Default: `document.hidden`, if there is a document. */
    hidden?: () => boolean;
    /** Plan one event at clock time `time`, lasting `duration` seconds. */
    schedule: (ev: ScoreEvent, time: number, duration: number) => Voice | null;
    /** Other things tied to beats (like dynamics), repeated with the loop. Sorted by beat. */
    cues?: readonly C[] | undefined;
    /** `beat` counts from the start like the notes (across loop passes). */
    onCue?: ((cue: C, time: number, beat: number) => void) | undefined;
    /** Called while planning, once for every whole beat, with its clock time. */
    onBeat?: ((beat: number, time: number) => void) | undefined;
    /** Called once when the score has played to its end (not after `stop()`). */
    onEnd?: () => void;
}
export interface Scheduler {
    /** Clock time of the end; `Infinity` when looping without `until`. */
    readonly endTime: number;
    /** Everything up to this beat has been planned. */
    readonly planned: number;
    readonly running: boolean;
    /**
     * Stop at clock time `at`: notes before it are still planned, every voice
     * is stopped at `at` with a short release.
     */
    stop(at: number): void;
}
export declare function startScheduler<C extends {
    beat: number;
}>(options: SchedulerOptions<C>): Scheduler;
//# sourceMappingURL=scheduler.d.ts.map