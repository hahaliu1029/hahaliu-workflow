#!/usr/bin/env python3
"""Grader attestation gate: seal a reviewed draft into scoreable final results.

The runner's results-draft.jsonl defaults every grader-judgment field to clean
(violation bits false, must/forbid empty) — so the scorer REJECTS drafts. This
tool seals the CURRENT content of the draft as results-final.jsonl and records
an attestation (grader, time, run_id, results_sha256) that the scorer verifies
before it will print an event-tier ALL CLEAN.

Honest limit: finalizing ASSERTS the grader reviewed the violation bits and
must/forbid against the transcripts; the tool records that assertion — it
cannot verify the review actually happened.

Usage: finalize-results.py <run-dir> --grader <name> [--results FILE] [--force]
  <run-dir> must hold manifest.json; FILE defaults to <run-dir>/results-draft.jsonl.
  Writes <run-dir>/results-final.jsonl + <run-dir>/attestation.json atomically;
  refuses symlinks and refuses to overwrite existing outputs without --force.
"""
import hashlib
import json
import os
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import consult_path_check as cpc

MAX_RESULTS = 4194304


def fail(msg):
    sys.stderr.write('finalize-results: ' + msg + '\n')
    sys.exit(2)


def atomic_write(path, data):
    if os.path.islink(path):
        fail('refusing to write through a symlink: ' + path)
    tmp = path + '.tmp.%d' % os.getpid()
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main(argv):
    args = list(argv[1:])
    force = '--force' in args
    args = [a for a in args if a != '--force']
    grader = results = None
    if '--grader' in args:
        i = args.index('--grader')
        if i + 1 >= len(args):
            fail('--grader requires a value')
        grader = args[i + 1]
        del args[i:i + 2]
    if '--results' in args:
        i = args.index('--results')
        if i + 1 >= len(args):
            fail('--results requires a value')
        results = args[i + 1]
        del args[i:i + 2]
    if len(args) != 1 or not (grader and grader.strip()):
        fail('usage: finalize-results.py <run-dir> --grader <name> [--results FILE] [--force]')
    rd = args[0]
    if not os.path.isdir(rd):
        fail('not a directory: ' + rd)
    mdata, merr = cpc.read_regular_file(os.path.join(rd, 'manifest.json'), 1048576, label='manifest')
    if merr:
        fail(merr)
    try:
        manifest = json.loads(mdata.decode('utf-8'))
        run_id = manifest['run_id']
    except Exception as e:
        fail('manifest.json invalid: %s' % e)
    results = results or os.path.join(rd, 'results-draft.jsonl')
    rdata, rerr = cpc.read_regular_file(results, MAX_RESULTS, label='results')
    if rerr:
        fail(rerr)
    # Per-case review evidence. The runner writes every grader-judgment field at its
    # clean default and writes NO grader_review, so an untouched draft can no longer be
    # sealed by supplying a name: the grader must annotate each case explicitly. This
    # still cannot prove a review happened — it just stops the zero-effort path.
    reviewed_n = 0
    for i, ln in enumerate(rdata.decode('utf-8').splitlines(), 1):
        if not ln.strip():
            continue
        try:
            row = json.loads(ln)
        except Exception:
            fail('results line %d is not valid JSON' % i)
        if not isinstance(row, dict):
            fail('results line %d is not a JSON object' % i)
        gr = row.get('grader_review')
        if not (isinstance(gr, dict) and gr.get('reviewed') is True
                and isinstance(gr.get('note'), str) and gr['note'].strip()):
            fail('results line %d (%s) 缺 grader_review={"reviewed":true,"note":"<对照轨迹的复核结论>"}'
                 ' —— 未逐 case 复核的 draft 不得定稿' % (i, row.get('id', '?')))
        reviewed_n += 1
    if not reviewed_n:
        fail('results 为空,无可定稿的用例')
    final = os.path.join(rd, 'results-final.jsonl')
    att = os.path.join(rd, 'attestation.json')
    for p in (final, att):
        if os.path.exists(p) and not force:
            fail('already exists (use --force to re-finalize): ' + p)
        if os.path.islink(p):
            fail('refusing to touch a symlink (even with --force): ' + p)
    atomic_write(final, rdata)
    # manifest_sha256 binds the attestation to THIS set of transcripts: touching
    # any transcript and regenerating the manifest (--force) invalidates it —
    # the grader's review claim never transfers to evidence they did not see
    record = {'grader': grader.strip(), 'time': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
              'run_id': run_id, 'results_sha256': hashlib.sha256(rdata).hexdigest(),
              'manifest_sha256': hashlib.sha256(mdata).hexdigest(),
              'reviewed_cases': reviewed_n,
              'attestation_kind': 'HUMAN-ATTESTED',
              'reviewed': '%d 例逐 case 附 grader_review;工具记录的是复核断言,不是复核发生的证明' % reviewed_n}
    atomic_write(att, (json.dumps(record, ensure_ascii=False, indent=1) + '\n').encode('utf-8'))
    print('finalized (HUMAN-ATTESTED, %d cases): %s\nattestation: %s (grader=%s, run_id=%s)'
          % (reviewed_n, final, att, grader.strip(), run_id))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
