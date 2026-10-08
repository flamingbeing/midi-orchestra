/** What `encodeWav` reads of an AudioBuffer. */
export interface AudioData {
    readonly numberOfChannels: number;
    readonly sampleRate: number;
    readonly length: number;
    getChannelData(channel: number): Float32Array;
}
export interface WavOptions {
    /** 16-bit integer PCM (default) or 32-bit float. */
    bitDepth?: 16 | 32;
}
/**
 * A WAV file of the audio, e.g. of `orch.render()`:
 *
 *     const url = URL.createObjectURL(new Blob([encodeWav(buffer)], { type: 'audio/wav' }));
 *
 * 16-bit samples are clipped to -1..1 and rounded.
 */
export declare function encodeWav(audio: AudioData, { bitDepth }?: WavOptions): ArrayBuffer;
//# sourceMappingURL=wav.d.ts.map