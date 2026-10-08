import type { Bus, BusOptions } from './types.ts';
export interface ImpulseOptions {
    /** Seconds of silence before the reverb starts. Default 12 ms. */
    predelay?: number;
    seed?: number;
}
/**
 * Impulse response for the reverb, computed instead of loaded: noise that
 * decays exponentially (-60 dB after `seconds`) and gets darker as it goes -
 * in real halls, air and walls swallow the highs first. Left and right get
 * their own noise and slightly different predelay, which makes the room wide.
 * Energy is normalized to 1, so a bus's `reverb` is a meaningful share.
 */
export declare function makeImpulse(sampleRate: number, seconds?: number, { predelay, seed }?: ImpulseOptions): [Float32Array, Float32Array];
/**
 * The reverb is shared: every bus sends its share into the same convolver.
 * One is enough for everything, and it is the most expensive node here.
 * Returns the node to send into.
 */
export declare function createReverb(ctx: BaseAudioContext, destination: AudioNode, seconds?: number): GainNode;
/**
 * Ramp a gain from wherever it is right now. cancelAndHoldAtTime holds the
 * value where a running fade currently is; without it (older Firefox),
 * `.value` has to do.
 */
export declare function rampFromNow(ctx: BaseAudioContext, param: AudioParam, target: number, seconds: number): void;
/**
 * The automatic makeup gain of a DynamicsCompressorNode (Web Audio spec):
 * the inverse of what the curve does to a full-scale signal, to the 0.6.
 */
export declare function makeupGain(thresholdDb: number, ratio: number): number;
/**
 * A limiter in front of `destination`: a fast compressor with a high ratio
 * that only acts near full scale, so that many loud notes at once do not
 * clip. The compressor's makeup gain is undone, so that everything below
 * the threshold passes unchanged. Browsers delay the signal by their
 * compressor lookahead (6 ms in Chromium). Returns the node to connect into.
 */
export declare function createLimiter(ctx: BaseAudioContext, destination: AudioNode): AudioNode;
/**
 * A mixer channel: level, pan, reverb share. Separate groups of sounds each
 * get their own, so they can be faded independently.
 */
export declare function createBus(ctx: BaseAudioContext, destination: AudioNode, reverbIn: AudioNode | null, { gain, reverb, pan }?: BusOptions): Bus;
//# sourceMappingURL=reverb.d.ts.map