// Pitch, level and sample selection - pure functions, no AudioContext.
export const midiToFreq = (midi) => 440 * Math.pow(2, (midi - 69) / 12);
/**
 * Playback rate that turns a sample of note `sampleMidi` into note `midi`.
 * `detune` is the requested detuning (cents), `tune` the measured detuning
 * of the recording (cents, from the manifest) - which is subtracted.
 */
export function playbackRate(midi, sampleMidi, detune = 0, tune = 0) {
    return Math.pow(2, (midi - sampleMidi + (detune - tune) / 100) / 12);
}
/**
 * Gain for a velocity. Quadratic, because that sounds reasonably even across
 * the whole range (0.5 = -12 dB) and stays audible down to 0.1 (-40 dB).
 * `sampleVel` is the velocity the sample was levelled for - the quiet
 * dynamic layer is already quieter in the file, hence the quotient.
 */
export function velocityGain(velocity, sampleVel = 1) {
    const v = Math.max(0, Math.min(1, velocity));
    return (v * v) / (sampleVel * sampleVel);
}
/**
 * Which dynamic layer: the quietest one that is at least as strong as
 * requested - a loud recording played softer sounds more natural than a quiet
 * one pushed up. If none is strong enough, the strongest.
 */
export function pickLayer(vels, velocity) {
    const sorted = [...new Set(vels)].sort((a, b) => a - b);
    for (const v of sorted)
        if (v >= velocity - 1e-9)
            return v;
    return sorted[sorted.length - 1];
}
/**
 * Closest sample to `midi` within the matching dynamic layer. On a tie the
 * lower one (which is then tuned up) - the point is being predictable.
 */
export function pickSample(samples, midi, velocity = 0.7) {
    if (!samples.length)
        return null;
    const layer = pickLayer(samples.map((s) => s.vel ?? 1), velocity);
    let best = null;
    for (const s of samples) {
        if ((s.vel ?? 1) !== layer)
            continue;
        const sm = s.midi ?? 0;
        if (!best) {
            best = s;
            continue;
        }
        const bm = best.midi ?? 0;
        const d = Math.abs(sm - midi);
        if (d < Math.abs(bm - midi) || (d === Math.abs(bm - midi) && sm < bm))
            best = s;
    }
    return best;
}
/**
 * Unpitched: random among the samples of the variant, but never the same one
 * twice in a row (you hear that immediately - the "machine gun" effect).
 * Unknown or missing variant -> the default.
 */
export function pickVariant(samples, variant, defaultVariant, last = null, random = Math.random) {
    let pool = samples.filter((s) => s.variant === variant);
    if (!pool.length)
        pool = samples.filter((s) => s.variant === defaultVariant);
    if (!pool.length)
        pool = [...samples];
    if (!pool.length)
        return null;
    if (pool.length > 1 && last)
        pool = pool.filter((s) => s !== last);
    return pool[Math.floor(random() * pool.length) % pool.length] ?? null;
}
//# sourceMappingURL=pitch.js.map