import type { ManifestSample } from './types.ts';
export declare const midiToFreq: (midi: number) => number;
/**
 * Playback rate that turns a sample of note `sampleMidi` into note `midi`.
 * `detune` is the requested detuning (cents), `tune` the measured detuning
 * of the recording (cents, from the manifest) - which is subtracted.
 */
export declare function playbackRate(midi: number, sampleMidi: number, detune?: number, tune?: number): number;
/**
 * Gain for a velocity. Quadratic, because that sounds reasonably even across
 * the whole range (0.5 = -12 dB) and stays audible down to 0.1 (-40 dB).
 * `sampleVel` is the velocity the sample was levelled for - the quiet
 * dynamic layer is already quieter in the file, hence the quotient.
 */
export declare function velocityGain(velocity: number, sampleVel?: number): number;
/**
 * Which dynamic layer: the quietest one that is at least as strong as
 * requested - a loud recording played softer sounds more natural than a quiet
 * one pushed up. If none is strong enough, the strongest.
 */
export declare function pickLayer(vels: readonly number[], velocity: number): number | undefined;
/** The fields `pickSample` looks at. */
export type PitchedSample = Pick<ManifestSample, 'vel'> & {
    midi?: number | null;
};
/**
 * Closest sample to `midi` within the matching dynamic layer. On a tie the
 * lower one (which is then tuned up) - the point is being predictable.
 */
export declare function pickSample<S extends PitchedSample>(samples: readonly S[], midi: number, velocity?: number): S | null;
/**
 * Unpitched: random among the samples of the variant, but never the same one
 * twice in a row (you hear that immediately - the "machine gun" effect).
 * Unknown or missing variant -> the default.
 */
export declare function pickVariant<S extends Pick<ManifestSample, 'variant'>>(samples: readonly S[], variant: string | undefined, defaultVariant: string | undefined, last?: S | null, random?: () => number): S | null;
//# sourceMappingURL=pitch.d.ts.map