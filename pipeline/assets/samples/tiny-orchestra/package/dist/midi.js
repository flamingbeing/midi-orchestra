// Standard MIDI File import: `parseMidi` reads the notes, tempo map and time
// signature of an SMF (format 0 or 1), `midiToScore` turns them into a score
// for the bundled instruments via General MIDI programs (or a mapping of your
// own). Pure, no dependencies.
class Reader {
    pos = 0;
    bytes;
    end;
    constructor(bytes, pos = 0, end = bytes.length) {
        this.bytes = bytes;
        this.pos = pos;
        this.end = end;
    }
    u8() {
        if (this.pos >= this.end)
            throw new Error(`MIDI: unexpected end of data at byte ${this.pos}`);
        return this.bytes[this.pos++];
    }
    u16() {
        return (this.u8() << 8) | this.u8();
    }
    u32() {
        return ((this.u16() << 16) | this.u16()) >>> 0;
    }
    /** Variable-length quantity: 7 bits per byte, high bit set on all but the last (at most 4 bytes). */
    vlq() {
        let n = 0;
        for (let i = 0; i < 4; i++) {
            const b = this.u8();
            n = n * 128 + (b & 0x7f);
            if (!(b & 0x80))
                return n;
        }
        throw new Error(`MIDI: variable-length number too long at byte ${this.pos}`);
    }
    take(n) {
        if (this.pos + n > this.end)
            throw new Error(`MIDI: unexpected end of data at byte ${this.pos}`);
        const out = this.bytes.subarray(this.pos, this.pos + n);
        this.pos += n;
        return out;
    }
    tag() {
        return String.fromCharCode(...this.take(4));
    }
}
/** Track names are usually ASCII; fall back to Latin-1 when they are not valid UTF-8. */
function text(bytes) {
    try {
        return new TextDecoder('utf-8', { fatal: true }).decode(bytes);
    }
    catch {
        return String.fromCharCode(...bytes);
    }
}
/**
 * Parse a Standard MIDI File (format 0 or 1, ticks-per-quarter division).
 * Note on with velocity 0 counts as note off; on/off of the same key on the
 * same channel of a track pair first in, first out, and notes still held end
 * with their track. Sysex and all other events are skipped. Throws on SMPTE
 * division, format 2 and malformed or truncated data.
 */
export function parseMidi(data) {
    const bytes = data instanceof Uint8Array ? data : new Uint8Array(data);
    const r = new Reader(bytes);
    if (bytes.length < 14 || r.tag() !== 'MThd')
        throw new Error('MIDI: not a Standard MIDI File (no MThd header)');
    const headerLen = r.u32();
    if (headerLen < 6)
        throw new Error('MIDI: header too short');
    const format = r.u16();
    const trackCount = r.u16();
    const division = r.u16();
    r.take(headerLen - 6);
    if (format !== 0 && format !== 1)
        throw new Error(`MIDI: format ${format} is not supported (only 0 and 1)`);
    if (division & 0x8000)
        throw new Error('MIDI: SMPTE time division is not supported');
    if (division === 0)
        throw new Error('MIDI: division of 0 ticks per quarter note');
    const tracks = [];
    const tempos = [];
    const signatures = [];
    const programs = [];
    const raw = [];
    let order = 0;
    let lastTick = 0;
    while (tracks.length < trackCount) {
        if (r.pos >= bytes.length)
            throw new Error(`MIDI: expected ${trackCount} tracks, found ${tracks.length}`);
        const tag = r.tag();
        const len = r.u32();
        const start = r.pos;
        r.take(len);
        if (tag !== 'MTrk')
            continue; // unknown chunks are skipped, as the spec asks
        const t = new Reader(bytes, start, start + len);
        const index = tracks.length;
        const track = { name: undefined };
        const held = new Map();
        let tick = 0;
        let status = 0;
        while (t.pos < t.end) {
            tick += t.vlq();
            const b = t.u8();
            if (b === 0xff) {
                const type = t.u8();
                const body = t.take(t.vlq());
                if (type === 0x2f)
                    break; // end of track
                if (type === 0x51 && body.length >= 3) {
                    const us = (body[0] << 16) | (body[1] << 8) | body[2];
                    // microseconds per quarter note; to 1/1000 bpm, so 90 bpm stays 90 and not 89.99995
                    if (us > 0)
                        tempos.push({ tick, order: order++, bpm: Math.round(60e9 / us) / 1000 });
                }
                else if (type === 0x58 && body.length >= 2) {
                    signatures.push({ tick, order: order++, num: body[0], den: 2 ** body[1] });
                }
                else if (type === 0x03 && track.name === undefined) {
                    track.name = text(body);
                }
            }
            else if (b === 0xf0 || b === 0xf7) {
                t.take(t.vlq()); // sysex
            }
            else if (b >= 0xf0) {
                throw new Error(`MIDI: unexpected status byte 0x${b.toString(16)} in track ${index}`);
            }
            else {
                // Running status: a data byte repeats the last channel status.
                if (b & 0x80)
                    status = b;
                else if (status)
                    t.pos--;
                else
                    throw new Error(`MIDI: data byte without status in track ${index}`);
                const kind = status & 0xf0;
                const channel = status & 0x0f;
                const d1 = t.u8() & 0x7f;
                const d2 = kind === 0xc0 || kind === 0xd0 ? 0 : t.u8();
                if (kind === 0xc0) {
                    programs.push({ tick, order: order++, track: index, channel, program: d1 });
                }
                else if (kind === 0x90 && d2 > 0) {
                    const key = channel * 128 + d1;
                    const list = held.get(key) ?? [];
                    list.push({ tick, vel: d2 });
                    held.set(key, list);
                }
                else if (kind === 0x80 || kind === 0x90) {
                    const on = held.get(channel * 128 + d1)?.shift();
                    if (on)
                        raw.push({ track: index, channel, midi: d1, vel: on.vel, on: on.tick, off: tick });
                }
            }
        }
        for (const [key, list] of held) {
            for (const on of list)
                raw.push({ track: index, channel: key >> 7, midi: key & 0x7f, vel: on.vel, on: on.tick, off: tick });
        }
        lastTick = Math.max(lastTick, tick);
        tracks.push(track);
    }
    const byTime = (a, b) => a.tick - b.tick || a.order - b.order;
    tempos.sort(byTime);
    signatures.sort(byTime);
    programs.sort(byTime);
    const tempo = [];
    for (const { tick, bpm } of tempos) {
        const beat = tick / division;
        const last = tempo[tempo.length - 1];
        if (last && last[0] === beat)
            last[1] = bpm; // the last of several at once wins
        else if (!last || last[1] !== bpm)
            tempo.push([beat, bpm]);
    }
    if (tempo[0]?.[0] !== 0)
        tempo.unshift([0, 120]);
    const sig = signatures[0];
    const timeSignature = sig && sig.num > 0 ? [sig.num, sig.den] : [4, 4];
    // Program changes act on the channel for all tracks, but files with the
    // same channel in several tracks rely on the track's own changes: use
    // those first.
    const programAt = (track, channel, tick) => {
        let own;
        let any;
        for (const p of programs) {
            if (p.tick > tick)
                break;
            if (p.channel !== channel)
                continue;
            any = p.program;
            if (p.track === track)
                own = p.program;
        }
        return own ?? any ?? 0;
    };
    const notes = raw
        .sort((a, b) => a.on - b.on || a.track - b.track || a.midi - b.midi)
        .map((n) => ({
        track: n.track,
        channel: n.channel,
        program: programAt(n.track, n.channel, n.on),
        midi: n.midi,
        velocity: n.vel / 127,
        beat: n.on / division,
        length: (n.off - n.on) / division,
    }));
    return {
        format,
        ticksPerBeat: division,
        tempo,
        timeSignature,
        beatsPerBar: (timeSignature[0] * 4) / timeSignature[1],
        lengthBeats: lastTick / division,
        tracks,
        notes,
    };
}
const round = (x) => Math.round(x * 1e6) / 1e6;
function median(notes) {
    const keys = notes.map((n) => n.midi).sort((a, b) => a - b);
    if (!keys.length)
        return 60;
    const mid = keys.length >> 1;
    return keys.length % 2 ? keys[mid] : (keys[mid - 1] + keys[mid]) / 2;
}
/** The member of a family whose lowest median pitch the group reaches: `[minMedian, name]`, high first. */
function pick(notes, family) {
    const m = median(notes);
    for (const [min, name] of family)
        if (m >= min)
            return name;
    return family[family.length - 1][1];
}
const STRINGS = [[67, 'violins'], [55, 'violas'], [43, 'celli'], [0, 'basses']];
const BRASS = [[65, 'trumpet'], [55, 'horn'], [43, 'trombone'], [0, 'tuba']];
const WINDS = [[76, 'flute'], [67, 'oboe'], [55, 'clarinet'], [0, 'bassoon']];
const PIZZ = [[55, 'violinsPizz'], [0, 'celliPizz']];
/**
 * Bundled instrument for a General MIDI program. Ensembles (strings, choir,
 * pads, organs -> strings; brass section -> brass; saxophones -> winds) and
 * pizzicato pick the family member by the group's median pitch; pianos,
 * guitars and anything without a closer match play on the harp.
 */
export function gmInstrument(group) {
    const p = group.program;
    const notes = group.notes;
    if (p >= 8 && p <= 10 || p === 14)
        return 'glockenspiel';
    if (p >= 11 && p <= 13)
        return 'marimba';
    if (p >= 16 && p <= 23)
        return pick(notes, STRINGS); // organs, accordion
    if (p === 40)
        return 'violins';
    if (p === 41)
        return 'violas';
    if (p === 42)
        return 'celli';
    if (p === 43)
        return 'basses';
    if (p === 44)
        return pick(notes, STRINGS); // tremolo strings
    if (p === 45)
        return pick(notes, PIZZ);
    if (p === 46)
        return 'harp';
    if (p === 47)
        return 'timpani';
    if (p >= 48 && p <= 55)
        return pick(notes, STRINGS); // string ensembles, choir, voices
    if (p === 56 || p === 59)
        return 'trumpet';
    if (p === 57)
        return 'trombone';
    if (p === 58)
        return 'tuba';
    if (p === 60)
        return 'horn';
    if (p >= 61 && p <= 63)
        return pick(notes, BRASS);
    if (p >= 64 && p <= 67)
        return pick(notes, WINDS); // saxophones
    if (p === 68 || p === 69)
        return 'oboe';
    if (p === 70)
        return 'bassoon';
    if (p === 71)
        return 'clarinet';
    if (p >= 72 && p <= 79)
        return 'flute';
    if (p >= 88 && p <= 95)
        return pick(notes, STRINGS); // pads
    return 'harp';
}
const DRUMS = {
    35: { instrument: 'bassdrum', variant: 'hit' },
    36: { instrument: 'bassdrum', variant: 'hit' },
    38: { instrument: 'snare', variant: 'hit' },
    40: { instrument: 'snare', variant: 'hit' },
    49: { instrument: 'cymbal', variant: 'crash' },
    52: { instrument: 'cymbal', variant: 'crash' },
    55: { instrument: 'cymbal', variant: 'crash' },
    57: { instrument: 'cymbal', variant: 'crash' },
    51: { instrument: 'cymbal', variant: 'soft' },
    53: { instrument: 'cymbal', variant: 'soft' },
    59: { instrument: 'cymbal', variant: 'soft' },
    75: { instrument: 'woodblock', variant: 'claves' },
    76: { instrument: 'woodblock', variant: 'hit' },
    77: { instrument: 'woodblock', variant: 'hit' },
    80: { instrument: 'triangle', variant: 'muted' },
    81: { instrument: 'triangle', variant: 'hit' },
};
/** Bundled instrument for a General MIDI percussion key; null for keys without one (hi-hats, toms, ...). */
export function gmDrum(key) {
    return DRUMS[key] ?? null;
}
/**
 * A score from a parsed MIDI file. Pitched notes are grouped by track,
 * channel and program, and each group becomes a part of the instrument
 * `options.instrument` names for it; percussion (channel index 9) becomes
 * one part per instrument that `options.drums` maps its keys to, with the
 * variant on every note. Parts are named after their track, else their
 * instrument (made unique with " 2", " 3", ...). The length is rounded up
 * to whole bars.
 *
 * The defaults map to the bundled instruments; with other instrument names,
 * pass both `instrument` and `drums` (or `drums: false`).
 */
export function midiToScore(data, options = {}) {
    const instrument = options.instrument ?? gmInstrument;
    const drums = options.drums === undefined ? gmDrum : options.drums;
    const groups = new Map();
    const drumParts = new Map();
    for (const n of data.notes) {
        if (drums && n.channel === 9) {
            const hit = drums(n.midi, n);
            if (!hit)
                continue;
            const list = drumParts.get(hit.instrument) ?? [];
            list.push([round(n.beat), null, round(n.length), round(n.velocity), hit.variant]);
            drumParts.set(hit.instrument, list);
            continue;
        }
        const id = `${n.track}:${n.channel}:${n.program}`;
        let g = groups.get(id);
        if (!g) {
            g = { track: n.track, trackName: data.tracks[n.track]?.name, channel: n.channel, program: n.program, notes: [] };
            groups.set(id, g);
        }
        g.notes.push(n);
    }
    const used = new Set();
    const unique = (name) => {
        let out = name;
        for (let i = 2; used.has(out); i++)
            out = `${name} ${i}`;
        used.add(out);
        return out;
    };
    const parts = [];
    const sorted = [...groups.values()].sort((a, b) => a.track - b.track || a.channel - b.channel); // programs in order of appearance
    for (const g of sorted) {
        const inst = instrument(g);
        if (inst === null)
            continue;
        parts.push({
            instrument: inst,
            name: unique(g.trackName?.trim() || inst),
            notes: g.notes.map((n) => [round(n.beat), n.midi, round(n.length), round(n.velocity)]),
        });
    }
    for (const [inst, notes] of drumParts)
        parts.push({ instrument: inst, name: unique(inst), notes });
    const bar = data.beatsPerBar > 0 ? data.beatsPerBar : 4;
    let end = data.lengthBeats;
    for (const p of parts)
        for (const [beat, , len] of p.notes)
            end = Math.max(end, beat + len);
    const bars = Math.max(1, Math.ceil(round(end / bar)));
    const score = { bpm: data.tempo[0]?.[1] ?? 120, beatsPerBar: bar, lengthBeats: round(bars * bar), parts };
    if (data.tempo.length > 1)
        score.tempo = data.tempo.map(([beat, bpm]) => [round(beat), bpm]);
    return score;
}
//# sourceMappingURL=midi.js.map