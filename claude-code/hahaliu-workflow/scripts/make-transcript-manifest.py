#!/usr/bin/env python3
"""Generate manifest.json for a transcript directory captured by the execution runner.

Trust boundary (stated honestly): this tool makes the manifest DETERMINISTIC —
sha256/case_id/run_id/model metadata are derived from the captured files, never
hand-authored. It does NOT prove provenance: a scorer can only trust the result
if the directory itself was produced by a trusted runner. Forged directories are
outside the trust boundary by design; the scorer says so in its output.

Contract per transcript file <case_id>.jsonl:
  - JSONL, first line  {"type":"runner_start","case_id":...,"run_id":...,
                        "main_model":...,"secondary_model":...|null, ...}
  - last line          {"type":"runner_end","case_id":...,"run_id":...}
  - filename stem must equal the case_id in the markers

Usage: make-transcript-manifest.py <dir> --run-id <ID> [--force]
  Models are read from each runner_start marker (main_model required there).
  Writes <dir>/manifest.json; refuses to overwrite without --force.
"""
import hashlib
import json
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import consult_path_check as cpc

MAX_TRANSCRIPT = 4194304  # same bound as the scorer's transcript reader


def fail(msg):
    sys.stderr.write('make-transcript-manifest: ' + msg + '\n')
    sys.exit(2)


def main(argv):
    args = [a for a in argv[1:]]
    force = '--force' in args
    args = [a for a in args if a != '--force']
    run_id = None
    if '--run-id' in args:
        i = args.index('--run-id')
        if i + 1 >= len(args):
            fail('--run-id requires a value')
        run_id = args[i + 1]
        del args[i:i + 2]
    if len(args) != 1 or not run_id or not run_id.strip():
        fail('usage: make-transcript-manifest.py <dir> --run-id <ID> [--force]')
    d = args[0]
    if not os.path.isdir(d):
        fail('not a directory: ' + d)
    out = os.path.join(d, 'manifest.json')
    if os.path.islink(out):
        # refused even with --force: a symlinked manifest.json would let a write
        # here clobber an arbitrary file the link points at
        fail('manifest.json must not be a symlink (refused even with --force): ' + out)
    if os.path.exists(out) and not force:
        fail('manifest.json already exists (use --force to regenerate): ' + out)
    cases = {}
    run_meta = {}
    meta_seen = False
    # results-*.jsonl (draft/final/copies) live in the same run dir but are NOT
    # transcripts — --force regeneration on a full run dir must skip them
    names = sorted(x for x in os.listdir(d)
                   if x.endswith('.jsonl') and not x.startswith('results-'))
    if not names:
        fail('no *.jsonl transcripts in ' + d)
    for fn in names:
        p = os.path.join(d, fn)
        cid = fn[:-len('.jsonl')]
        # shared race-safe bounded reader (symlink/FIFO/device reject, <=4MiB)
        raw, err = cpc.read_regular_file(p, MAX_TRANSCRIPT, label='transcript')
        if err:
            fail(fn + ': ' + err)
        try:
            lines = [ln for ln in raw.decode('utf-8').splitlines() if ln.strip()]
        except UnicodeDecodeError:
            fail(fn + ': not valid UTF-8')
        if not lines:
            fail(fn + ': empty transcript')
        try:
            head = json.loads(lines[0])
            tail = json.loads(lines[-1])
        except Exception as e:
            fail(fn + ': first/last line not valid JSON (%s)' % e)
        for o, t in ((head, 'runner_start'), (tail, 'runner_end')):
            if not (isinstance(o, dict) and o.get('type') == t):
                fail(fn + ': first/last line must be %s marker' % t)
            if o.get('case_id') != cid:
                fail(fn + ': marker case_id %r != filename stem %r' % (o.get('case_id'), cid))
            if o.get('run_id') != run_id:
                fail(fn + ': marker run_id %r != --run-id %r' % (o.get('run_id'), run_id))
        mm = head.get('main_model')
        if not (isinstance(mm, str) and mm.strip()):
            fail(fn + ': runner_start.main_model must be a non-empty string')
        sm = head.get('secondary_model')
        if not (sm is None or (isinstance(sm, str) and sm.strip())):
            fail(fn + ': runner_start.secondary_model must be non-empty string or null')
        cases[cid] = {'file': fn, 'sha256': hashlib.sha256(raw).hexdigest(),
                      'main_model': mm, 'secondary_model': sm}
        # per-run constants (claude version, full runner command) must agree
        # across every transcript of the run — lifted to manifest top level
        this_meta = {k: head.get(k) for k in ('claude_version', 'agent_cmd', 'test_mode') if k in head}
        if not meta_seen:
            run_meta = this_meta
            meta_seen = True
        elif json.dumps(this_meta, sort_keys=True) != json.dumps(run_meta, sort_keys=True):
            fail(fn + ': runner_start claude_version/agent_cmd differ across transcripts of one run')
    # atomic + symlink-proof: O_EXCL|O_NOFOLLOW temp file in the same dir, then
    # os.replace (rename replaces a link itself, never writes through it)
    tmp = out + '.tmp.%d' % os.getpid()
    man = {'run_id': run_id, 'cases': cases}
    man.update(run_meta)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(man, f, ensure_ascii=False, indent=1)
            f.write('\n')
        os.replace(tmp, out)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    sys.stdout.write('manifest.json written: %d case(s), run_id=%s\n' % (len(cases), run_id))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
