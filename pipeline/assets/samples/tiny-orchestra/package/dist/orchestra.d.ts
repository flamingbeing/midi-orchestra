import type { Bus, BusOptions, LoadOptions, Manifest, ManifestSample, NoteOptions, OrchestraOptions, Performance, PlayOptions, RenderOptions, Score, Voice } from './types.ts';
import type { InstrumentName } from './instruments.ts';
/** A manifest sample with its decoded audio. */
export interface LoadedSample extends ManifestSample {
    buffer: AudioBuffer;
    /** Seconds this browser's decoder moved the content (see decoderShift). */
    shift: number;
}
/**
 * The sampler. `I` is the set of instrument names it accepts: by default the
 * bundled ones, so a typo is a compile error. With a custom manifest use
 * `new Orchestra<string>(ctx, { manifest })` (inferred when you pass a
 * `Manifest<string>` object).
 */
export declare class Orchestra<I extends string = InstrumentName> {
    readonly ctx: BaseAudioContext;
    /** Folder of the sample files, with a trailing slash (or empty). */
    readonly baseUrl: string;
    readonly destination: AudioNode;
    private readonly manifestUrl;
    private manifestData;
    private manifestPromise;
    private readonly loading;
    private readonly ready;
    private readonly fetchLimited;
    private readonly options;
    /** Where buses and the reverb go: the limiter, or `destination`. */
    private readonly output;
    private readonly reverbIn;
    private readonly maxVoices;
    private defaultBus;
    constructor(ctx: BaseAudioContext, options?: OrchestraOptions<I>);
    static midiToFreq(midi: number): number;
    /** All instrument names in the manifest (empty until it has loaded). */
    get instruments(): I[];
    /** The loaded manifest, or null until `load()` has fetched it. */
    get manifest(): Manifest<I> | null;
    /** True once the instrument is decoded and playable. */
    has(instrument: I): boolean;
    /**
     * Load the manifest and the instruments (no argument: all of them). Never
     * throws - whatever is missing is simply missing, with a console warning.
     * Calling it again loads nothing twice.
     */
    load(instruments?: readonly I[], options?: LoadOptions): Promise<void>;
    private loadInstrument;
    /**
     * Forget instruments (no argument: all of them), so their audio can be
     * garbage collected. Notes that are sounding play on; a later `load()`
     * fetches them again.
     */
    unload(instruments?: readonly I[]): void;
    /**
     * Browsers keep an AudioContext suspended until the user interacts with
     * the page. This resumes it on the first click, touch or key press on
     * `target` (default: the document); the promise resolves once it runs.
     */
    unlock(target?: EventTarget): Promise<void>;
    private defaultOut;
    /**
     * A mixer channel: dry to `destination`, plus a `reverb` share into the
     * shared reverb. Give each group of sounds (say, the music and the sound
     * effects) a bus of its own, so they can be faded separately.
     */
    bus(options?: BusOptions): Bus;
    /**
     * One note at the absolute audio-clock time `at`. Returns null when the
     * instrument is not loaded (yet) - an app should not break just because
     * its samples are still on the way.
     */
    note(options: NoteOptions<I>): Voice | null;
    /** Make room for a voice at `t`: fade out the oldest if too many sound then. */
    private limitVoices;
    /**
     * Play a score. It is planned only a short stretch ahead (see
     * scheduler.ts), so `stop()` takes effect at once, loops run forever and
     * the tempo can change while it plays.
     */
    play(score: Score<I>, options?: PlayOptions): Performance;
    /**
     * Render a score offline, faster than real time, into an AudioBuffer -
     * e.g. for `encodeWav()`. Loads whatever instruments the score needs
     * first. Needs `OfflineAudioContext` (any browser).
     */
    render(score: Score<I>, options?: RenderOptions): Promise<AudioBuffer>;
    private perform;
}
//# sourceMappingURL=orchestra.d.ts.map