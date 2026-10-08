// Tempo: beats <-> seconds with tempo changes and gradual accelerando /
// ritardando, and the live timeline of a performance on top of it (start
// time, start beat, tempo changes while it plays). Pure, no AudioContext.
const valid = (bpm) => Number.isFinite(bpm) && bpm > 0;
/**
 * Tempo map from a base tempo and a list of changes. Changes before beat 0
 * or with an invalid tempo are ignored; the base tempo holds until the first
 * change (and before beat 0).
 */
export function tempoMap(bpm, changes = []) {
    const base = valid(bpm) ? bpm : 120;
    const points = changes
        .filter(([b, t]) => Number.isFinite(b) && b >= 0 && valid(t))
        .map(([beat, t, ramp]) => ({ beat, bpm: t, ramp: !!ramp }))
        .sort((a, b) => a.beat - b.beat);
    const segs = [{ beat: 0, sec: 0, bpm: base, slope: 0 }];
    for (const p of points) {
        const prev = segs[segs.length - 1];
        const len = p.beat - prev.beat;
        if (p.ramp && len > 0)
            prev.slope = (p.bpm - prev.bpm) / len;
        const sec = prev.sec + segSeconds(prev, len);
        if (len === 0)
            segs[segs.length - 1] = { beat: p.beat, sec, bpm: p.bpm, slope: 0 };
        else
            segs.push({ beat: p.beat, sec, bpm: p.bpm, slope: 0 });
    }
    const first = segs[0];
    return {
        seconds(beat) {
            if (beat < 0)
                return (beat * 60) / first.bpm;
            const s = findSeg(segs, (x) => x.beat <= beat);
            return s.sec + segSeconds(s, beat - s.beat);
        },
        beatAt(sec) {
            if (sec < 0)
                return (sec * first.bpm) / 60;
            const s = findSeg(segs, (x) => x.sec <= sec);
            return s.beat + segBeats(s, sec - s.sec);
        },
        bpmAt(beat) {
            if (beat < 0)
                return first.bpm;
            const s = findSeg(segs, (x) => x.beat <= beat);
            return s.bpm + s.slope * (beat - s.beat);
        },
    };
}
/** Last segment that satisfies `ok` (segments are sorted). */
function findSeg(segs, ok) {
    let lo = 0, hi = segs.length - 1;
    while (lo < hi) {
        const mid = (lo + hi + 1) >> 1;
        if (ok(segs[mid]))
            lo = mid;
        else
            hi = mid - 1;
    }
    return segs[lo];
}
// With the tempo rising linearly (bpm + slope * x), the time for x beats is
// the integral of 60 / tempo: 60 / slope * ln(1 + slope * x / bpm).
function segSeconds(s, beats) {
    if (Math.abs(s.slope) < 1e-12)
        return (beats * 60) / s.bpm;
    return (60 / s.slope) * Math.log(1 + (s.slope * beats) / s.bpm);
}
function segBeats(s, sec) {
    if (Math.abs(s.slope) < 1e-12)
        return (sec * s.bpm) / 60;
    return (s.bpm * (Math.exp((s.slope * sec) / 60) - 1)) / s.slope;
}
/**
 * A tempo map that repeats every `lengthBeats` - for loops, where each pass
 * starts again at the tempo of beat 0.
 */
export function repeating(map, lengthBeats) {
    if (!(lengthBeats > 0))
        return map;
    const pass = map.seconds(lengthBeats);
    return {
        seconds(beat) {
            if (beat < 0)
                return map.seconds(beat);
            const k = Math.floor(beat / lengthBeats);
            return k * pass + map.seconds(beat - k * lengthBeats);
        },
        beatAt(sec) {
            if (sec < 0)
                return map.beatAt(sec);
            const k = Math.floor(sec / pass);
            return k * lengthBeats + map.beatAt(sec - k * pass);
        },
        bpmAt(beat) {
            if (beat < 0)
                return map.bpmAt(beat);
            return map.bpmAt(beat - Math.floor(beat / lengthBeats) * lengthBeats);
        },
    };
}
/**
 * The timeline of a performance: `startBeat` sounds at `startTime`, and the
 * score's tempo map is played `factor` times as fast. `setFactor` changes
 * the speed from a given beat on, without moving anything before it.
 */
export class LiveTimeline {
    map;
    anchors;
    constructor(map, startTime, startBeat = 0, factor = 1) {
        this.map = map;
        this.anchors = [{ beat: startBeat, time: startTime, factor: factor > 0 ? factor : 1 }];
    }
    /** Current speed factor (of the last change). */
    get factor() {
        return this.anchors[this.anchors.length - 1].factor;
    }
    time(beat) {
        const a = this.find((x) => x.beat <= beat);
        return a.time + (this.map.seconds(beat) - this.map.seconds(a.beat)) / a.factor;
    }
    beat(time) {
        const a = this.find((x) => x.time <= time);
        return this.map.beatAt(this.map.seconds(a.beat) + (time - a.time) * a.factor);
    }
    /** Tempo (bpm) at `beat`, including the factor. */
    bpmAt(beat) {
        return this.map.bpmAt(beat) * this.find((x) => x.beat <= beat).factor;
    }
    /** From `beat` on, play `factor` times as fast as the tempo map. */
    setFactor(factor, beat) {
        if (!(factor > 0))
            return;
        const time = this.time(beat);
        // changes after `beat` are replaced
        while (this.anchors.length > 1 && this.anchors[this.anchors.length - 1].beat >= beat)
            this.anchors.pop();
        this.anchors.push({ beat, time, factor });
    }
    find(ok) {
        for (let i = this.anchors.length - 1; i > 0; i--)
            if (ok(this.anchors[i]))
                return this.anchors[i];
        return this.anchors[0];
    }
}
//# sourceMappingURL=tempo.js.map