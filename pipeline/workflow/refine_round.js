export const meta = {
  name: 'orchestral-refine-round',
  description: 'One refinement round on a piece: baseline verify, five critic lenses, fixer renders the next draft, independent verifier',
  phases: [
    { title: 'Setup', detail: 'baseline metrics for the current draft' },
    { title: 'Critique', detail: 'five lenses find measured realism problems' },
    { title: 'Fix', detail: 'implement verified improvements, render the next draft' },
    { title: 'Verify', detail: 'independent regression gate' },
  ],
}
// args: { repo: '/home/user/midi-orchestra', piece: 'Disney Medley', cur: 'draft9', next: 'draft10', py: 'python3',
//         work: '/tmp/midi-orchestra-work', deadline: '08:50 UTC' (optional) }
const R = args.repo || '/home/user/midi-orchestra'
const PIECE = `${R}/${args.piece}`
const CUR = args.cur, NEXT = args.next
const PY = args.py || 'python3'
const WORK = `${args.work || '/tmp/midi-orchestra-work'}/${args.piece}`
const COMMON = `Project: render the MIDI of "${args.piece}" as a faithful recording that sounds as close as possible to a real orchestra.
Faithfulness contract: notes, pitches and the tempo map of the MIDI are fixed; only articulation lengths and humanisation <= 30 ms may change (piece-specific tempo edits the listener asked for live in ${PIECE}/config/).
The listener can hear; we cannot. ${PIECE}/notes/USER_FEEDBACK.md is authoritative and nothing they liked may regress. Also read ${R}/pipeline/README.md and ${PIECE}/notes/*.md.
Layout: engine ${R}/pipeline/{prepare,render,mix}.py, one-command render ${R}/pipeline/run.sh "${PIECE}" <draft> (env PY=${PY} WORK=${args.work || '/tmp/midi-orchestra-work'}) -> ${WORK}/<draft>/{input.mid,stems/,master.wav} and ${PIECE}/drafts/<draft>.{mp3,m4a}. Piece settings (fermatas, balance targets, automation, extra tracks) are in ${PIECE}/config/piece.json - put piece-specific changes there, engine changes in pipeline/*.py behind an env switch defaulting to the new behaviour.
Verification: ${PY} ${R}/pipeline/tools/verify.py --stems DIR --master WAV --midi INPUT.mid [--prev-metrics JSON] --out JSON (pitch per note, onsets, clicks, loudness, melody masking, section arc, regressions).
HARD GATE (learned the hard way, draft 7): (a) per-note loudness consistency on the FULL piece (${R}/pipeline/tools/noteloud.py <stems> <input.mid>) must not get worse than ${CUR} for any instrument (resid SD and p90 adjacent jump, tolerance 0.3 dB); (b) the mix calibrates each instrument's loudness AFTER the hall to the TARGET table - keep that; (c) never adopt a technique on excerpt evidence alone - re-measure on the full piece. Prefer few, careful, well-verified changes over many.
Environment: renders take ~5 min on 4 CPUs; run heavy jobs one at a time. Disk is limited: delete intermediate WAVs, keep at most one extra stem set. Measure, don't guess; report numbers.${args.deadline ? `\nTIME LIMIT: ${NEXT} must be rendered, verified and exported by ${args.deadline} (check 'date -u'); if time runs short ship the verified subset of changes.` : ''}`

phase('Setup')
const setup = await agent(`${COMMON}\n\nTask: make sure ${CUR} exists in ${WORK}/${CUR}/ (stems + master.wav); if not, render it with run.sh. Run verify.py on it and save ${PIECE}/notes/metrics_${CUR}.json plus a short summary appended to ${PIECE}/notes/METRICS.md.`,
  { label: 'setup:baseline', phase: 'Setup', schema: { type: 'object', properties: { ok: { type: 'boolean' }, summary: { type: 'string' } }, required: ['ok', 'summary'] } })

const LENSES = [
  { key: 'performer', prompt: 'PERFORMER REALISM: how professional orchestral players would perform this within the fixed MIDI - wind breathing (phrase length per breath by dynamic/register), slurs vs re-tonguing, bow changes, phrase shaping, fermata and cadence timing, vibrato onset.' },
  { key: 'faithful-timing', prompt: 'FAITHFULNESS & TIMING: every MIDI note present at the right pitch/time per stem; tempo events, onset compensation differences between instruments, legato/trim offsets; fermatas and ritardandi natural; onset spread within chords; late or early entries.' },
  { key: 'instruments', prompt: 'INSTRUMENT REALISM per instrument: sample choice and articulation coverage, short-note level and timbre, legato joins, vibrato continuity, release tails, dynamic layers, round-robin variety, attack lag, loops, noise. Propose better free samples if the current ones limit realism.' },
  { key: 'balance', prompt: 'BALANCE & MUSICALITY: which instrument carries the tune at each moment and is it clearly on top; accompaniment masking; loudness consistency within phrases; dynamics arc; the listener feedback list.' },
  { key: 'hall-mix', prompt: 'HALL, MIX & MASTER vs real orchestral recordings: per-seat convolution levels, depth, width, low-mid mud, harshness, air, reverb tail, stereo balance, master dynamics (LRA, crest, limiter), tonal balance per family.' },
]
const FINDINGS = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: {
  severity: { type: 'string', enum: ['high', 'medium', 'low'] }, title: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } },
  required: ['severity', 'title', 'evidence', 'fix'] } } }, required: ['findings'] }

phase('Critique')
const crit = await parallel(LENSES.map(l => () => agent(`${COMMON}\n\nBaseline: ${JSON.stringify(setup)} (${PIECE}/notes/metrics_${CUR}.json).\nYou are a critic: do not modify the repo; scratch under ${WORK}/critic_${l.key}/ and delete large files when done. Lens: ${l.prompt}\nReport up to 8 measured problems ranked by how much they hurt realism, each with a concrete fix (file/function + change).`,
  { label: `critic:${l.key}`, phase: 'Critique', schema: FINDINGS })))
const findings = crit.flatMap((c, i) => (c ? c.findings.map(f => ({ lens: LENSES[i].key, ...f })) : []))
log(`critique: ${findings.length} findings (${findings.filter(f => f.severity === 'high').length} high)`)

phase('Fix')
const fixed = await agent(`${COMMON}\n\nYou are the fixer. Findings:\n${JSON.stringify(findings, null, 1)}\n\nFor each high/medium finding: verify the evidence first (skip with reason if it doesn't hold), implement it (engine change behind an env switch, or piece.json), A/B on a short excerpt where possible. Then render ${NEXT} with run.sh, run verify.py with --prev-metrics ${PIECE}/notes/metrics_${CUR}.json and save ${PIECE}/notes/metrics_${NEXT}.json. Revert any change that causes a REGRESSION. Delete ${WORK}/${CUR}/stems only after ${NEXT} verifies. Log changes in ${PIECE}/notes/changes_${NEXT}.md (plain language, plus a 3-6 bullet 'what you should hear differently' list for the listener).`,
  { label: 'fix', phase: 'Fix', schema: { type: 'object', properties: {
    applied: { type: 'array', items: { type: 'string' } }, skipped: { type: 'array', items: { type: 'string' } },
    mp3: { type: 'string' }, verify_summary: { type: 'string' }, listen_notes: { type: 'array', items: { type: 'string' } } },
    required: ['applied', 'skipped', 'mp3', 'verify_summary', 'listen_notes'] } })

phase('Verify')
const verdict = await agent(`${COMMON}\n\nIndependent verifier. Fixer report: ${JSON.stringify(fixed)}.\nRe-run verify.py yourself on ${NEXT} vs ${CUR}; spot-check every passage named in USER_FEEDBACK.md; confirm the mp3 exists, plays the full length, master -16 LUFS +-1, true peak <= -1 dBTP. If ${NEXT} regresses anything the listener cared about, say so (pass=false) and name the better version. Fix only trivial defects.`,
  { label: 'verify', phase: 'Verify', schema: { type: 'object', properties: {
    pass: { type: 'boolean' }, better_version: { type: 'string' }, mp3: { type: 'string' }, regressions: { type: 'array', items: { type: 'string' } }, notes: { type: 'string' } },
    required: ['pass', 'better_version', 'mp3', 'regressions', 'notes'] } })
return { setup, findings, fixed, verdict }
