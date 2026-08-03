#!/usr/bin/env python3
"""Execution-tier eval runner: dispatches cold-test agents headlessly and produces
a PRIVATE run directory whose evidence chain excludes the model under test.

What the RUNNER process (not the agent) does in-process:
  - creates the run dir (mode 700) and per-case transcript files (mode 600)
  - writes runner_start / phase / phase_result / runner_end marker events
  - captures the agent's stream-json stdout verbatim as JSONL events
  - derives manifest.json via make-transcript-manifest.py (never hand-written)
  - assembles results-draft.jsonl mechanically from each phase's final JSON line

The agent only ever answers prompts; it is never told the run dir, never writes
markers, transcripts, manifest, or result rows. Honest limits: the draft rows'
violation bits (dual_chain/unauthorized/done_without_verification) and
must_missing/forbid_present are GRADER judgments — the runner defaults them to
clean and the score is NOT final evidence until a grader reviews the transcripts.

Usage:
  run-evals.py --tier gate|periodic|all|orch --model <model-id> [--cases id,id,...]
               [--out ROOT] [--timeout SECS]

tier=orch is the EXECUTION tier: the agent gets real Agent/Read/Write/Edit tools
(+ --forward-subagent-text so subagent events carry parent_tool_use_id), and the
phase CWD is seeded from evals/orch-fixtures/<case-id>/ — a private sandbox copy,
still unrelated to the run dir. Recommend --timeout 900 for real orch runs.

Env:
  RUNNER_AGENT_CMD  override the agent command (shlex-split; the prompt is written
                    to the agent's stdin — never argv, so variadic flags like
                    --allowedTools cannot swallow it). Default:
                    claude -p --output-format stream-json --verbose \
                           --model <model-id> --allowedTools Read
                    The override is also the selftest stub seam.

Scoring (strict transcript coverage is the default with --transcripts):
  validate-workflow.sh --score <run-dir>/results-draft.jsonl --tier <tier> \
                       --transcripts <run-dir>
"""
import hashlib
import json
import os
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
VALIDATOR = os.path.join(HERE, 'validate-workflow.sh')
MANIFESTER = os.path.join(HERE, 'make-transcript-manifest.py')
BLOCK_RE = re.compile(r'^--- case (\S+) \[(\S+)\] (activation|routing|protocol|orchestration) ---$')
PHASES = ('activation', 'routing', 'protocol', 'orchestration')
FIXROOT = os.path.join(os.path.dirname(HERE), 'evals', 'orch-fixtures')


def fail(msg):
    sys.stderr.write('run-evals: ' + msg + '\n')
    sys.exit(2)


def parse_args(argv):
    a = {'tier': None, 'model': None, 'cases': None, 'out': None, 'timeout': 600}
    i = 1
    while i < len(argv):
        k = argv[i]
        if k in ('--tier', '--model', '--cases', '--out', '--timeout'):
            if i + 1 >= len(argv):
                fail(k + ' requires a value')
            v = argv[i + 1]
            a[k[2:]] = int(v) if k == '--timeout' else v
            i += 2
        else:
            fail('unknown argument: ' + k)
    if a['tier'] not in ('gate', 'periodic', 'all', 'orch'):
        fail('--tier must be gate|periodic|all|orch')
    if not (a['model'] and a['model'].strip()):
        fail('--model is required (recorded as manifest main_model — no guessing)')
    return a


def parse_emission(text):
    """emission text -> {case_id: {phase: prompt}} preserving phase order."""
    prompts = {}
    cur = None
    buf = []
    def flush():
        if cur:
            body = '\n'.join(buf).strip()
            if body:
                prompts.setdefault(cur[0], {})[cur[1]] = body
    for ln in text.splitlines():
        m = BLOCK_RE.match(ln)
        if m:
            flush()
            cur = (m.group(1), m.group(3))
            buf = []
        elif ln.startswith('=== '):
            flush()
            cur = None
            buf = []
        elif cur:
            buf.append(ln)
    flush()
    return prompts


def agent_cmd(model, phase):
    ov = os.environ.get('RUNNER_AGENT_CMD')
    if ov:
        return shlex.split(ov)
    # cold environment: --safe-mode (no user/project customizations, plugins,
    # hooks), --no-session-persistence, --no-chrome — Phase A's "frontmatter-only"
    # premise must not be polluted by ambient rules. Phase A gets NO tools (its
    # prompt forbids reading); routing/protocol prompts REQUIRE reading live
    # files, so they get Read and nothing else.
    base = ['claude', '-p', '--output-format', 'stream-json', '--verbose',
            '--model', model, '--safe-mode', '--no-session-persistence', '--no-chrome']
    if phase == 'activation':
        return base + ['--tools', '']
    if phase == 'orchestration':
        # execution tier: real Agent dispatch in the sandbox CWD; subagent events
        # must carry parent_tool_use_id or the ownership audit is blind
        return base + ['--tools', 'Agent,Read,Write,Edit',
                       '--allowedTools', 'Agent,Read,Write,Edit', '--forward-subagent-text']
    return base + ['--tools', 'Read', '--allowedTools', 'Read']


def last_json_line(text):
    """last parseable {...} line of an agent's result text -> (obj, raw) or (None, None)."""
    if not isinstance(text, str):
        return None, None
    for ln in reversed([l.strip() for l in text.splitlines() if l.strip()]):
        if ln.startswith('{') and ln.endswith('}'):
            try:
                return json.loads(ln), ln
            except Exception:
                continue
    return None, None


def snapshot_tree(root, max_files=500):
    """{relpath: {sha256, size}} inventory of a sandbox tree (bounded)."""
    inv = {}
    n = 0
    for dirpath, _dirs, files in os.walk(root):
        for fn in sorted(files):
            n += 1
            if n > max_files:
                inv['__truncated__'] = {'sha256': None, 'size': None}
                return inv
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, root)
            try:
                h = hashlib.sha256()
                with open(p, 'rb') as f:
                    for chunk in iter(lambda: f.read(65536), b''):
                        h.update(chunk)
                inv[rel] = {'sha256': h.hexdigest(), 'size': os.path.getsize(p)}
            except OSError:
                inv[rel] = {'sha256': None, 'size': None}
    return inv


def sandbox_state_event(phase, cwd, before):
    """Runner-authored before/after evidence: the trace must prove writes actually
    LANDED (hash delta), not merely that Write/Edit tool calls appeared."""
    after = snapshot_tree(cwd)
    changed = sorted(f for f in after if f in before and before[f] != after[f] and f != '__truncated__')
    added = sorted(f for f in after if f not in before and f != '__truncated__')
    deleted = sorted(f for f in before if f not in after and f != '__truncated__')
    content = {}
    total = 0
    trunc = False
    for f in changed + added:
        try:
            with open(os.path.join(cwd, f), 'rb') as fh:
                b = fh.read(16385)
        except OSError:
            continue
        if len(b) > 16384 or total + len(b) > 262144:
            trunc = True
            continue
        try:
            content[f] = b.decode('utf-8')
        except UnicodeDecodeError:
            trunc = True
            continue
        total += len(b)
    # snapshot_tree caps the walk at max_files and marks the cut with __truncated__.
    # Past that cap a real mutation simply never reaches changed/added/deleted, so an
    # incomplete inventory can never prove "nothing was written" — the scorer must
    # refuse to score it rather than read the empty delta as a clean run.
    complete = '__truncated__' not in before and '__truncated__' not in after
    return {'type': 'sandbox_state', 'phase': phase, 'sandbox': os.path.realpath(cwd), 'before': before,
            'after': after, 'changed': changed, 'added': added, 'deleted': deleted,
            'after_content': content, 'content_truncated': trunc, 'inventory_complete': complete}


def run_phase(cmd, prompt, tf, phase, timeout, fixture=None):
    """Dispatch one agent, stream its stdout into the transcript, return result text.

    Each phase gets a fresh random temp CWD with NO ancestry relation to the run
    dir — a Read-capable agent must not be able to reach ../<case>.jsonl or any
    other evidence; the dir is removed as soon as the phase ends. For the
    orchestration phase the CWD is seeded with a copy of the case's sandbox
    fixture tree (the copy, never the install-dir original, is what agents touch),
    and a sandbox_state before/after inventory is captured before removal."""
    tf.write(json.dumps({'type': 'phase', 'phase': phase}) + '\n')
    cwd = tempfile.mkdtemp(prefix='hahaliu-eval-cwd-')
    if fixture:
        shutil.copytree(fixture, cwd, dirs_exist_ok=True)
    before = snapshot_tree(cwd) if fixture else None
    sstate = None
    timed_out = False
    partial = None
    proc = None
    try:
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                              timeout=timeout, cwd=cwd)
    except subprocess.TimeoutExpired as te:
        # keep the partial stream: the events produced before the kill are real
        # diagnostics (they showed orch-04's 900s timeout was healthy-but-slow)
        timed_out = True
        po = te.output
        if isinstance(po, bytes):
            po = po.decode('utf-8', 'replace')
        partial = po
    finally:
        if fixture is not None:
            sstate = sandbox_state_event(phase, cwd, before)
        shutil.rmtree(cwd, ignore_errors=True)

    def stream_events(text):
        res = None
        for ln in (text or '').splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                ev = json.loads(ln)
            except Exception:
                tf.write(json.dumps({'type': 'raw', 'text': ln}, ensure_ascii=False) + '\n')
                continue
            tf.write(ln + '\n')
            # a rc=0 process can still end in an ERROR result event — only an explicit
            # success terminal state counts, otherwise the phase is a failure and the
            # case gets excluded from the draft (runner then exits non-zero)
            if (isinstance(ev, dict) and ev.get('type') == 'result'
                    and ev.get('subtype') == 'success' and ev.get('is_error') is not True
                    and isinstance(ev.get('result'), str)):
                res = ev['result']
        return res

    if timed_out:
        stream_events(partial)
        if sstate is not None:
            tf.write(json.dumps(sstate, ensure_ascii=False) + '\n')
        tf.write(json.dumps({'type': 'phase_result', 'phase': phase, 'exit': -1,
                             'result': None, 'error': 'timeout'}) + '\n')
        return None, -1
    res_text = stream_events(proc.stdout)
    if sstate is not None:
        tf.write(json.dumps(sstate, ensure_ascii=False) + '\n')
    tf.write(json.dumps({'type': 'phase_result', 'phase': phase, 'exit': proc.returncode,
                         'result': res_text is not None}, ensure_ascii=False) + '\n')
    return res_text, proc.returncode


def main(argv):
    a = parse_args(argv)
    em = subprocess.run([VALIDATOR, '--evals=' + a['tier']], capture_output=True, text=True)
    if em.returncode != 0:
        fail('emission failed: ' + (em.stderr or em.stdout)[-400:])
    prompts = parse_emission(em.stdout)
    if not prompts:
        fail('no dispatch prompts parsed from emission')
    sel = sorted(prompts)
    if a['cases']:
        want = [c.strip() for c in a['cases'].split(',') if c.strip()]
        unknown = [c for c in want if c not in prompts]
        if unknown:
            fail('unknown case id(s): ' + ' '.join(unknown))
        sel = want
    root = a['out'] or os.path.join(os.environ.get('XDG_CACHE_HOME')
                                    or os.path.expanduser('~/.cache'), 'hahaliu-workflow', 'runs')
    os.makedirs(root, exist_ok=True)
    run_id = time.strftime('%Y%m%d-%H%M%S') + '-' + secrets.token_hex(4)
    rd = os.path.join(root, run_id)
    os.makedirs(rd)
    os.chmod(rd, 0o700)   # private: transcripts may quote repo content
    claude_version = None
    if not os.environ.get('RUNNER_AGENT_CMD'):
        try:
            vv = subprocess.run(['claude', '--version'], capture_output=True, text=True, timeout=30)
            claude_version = vv.stdout.strip() or None
        except Exception:
            claude_version = None
    cmds = {ph: agent_cmd(a['model'], ph) for ph in PHASES}
    results = []
    warns = []
    for cid in sel:
        tp = os.path.join(rd, cid + '.jsonl')
        res = {}
        case_ok = True
        with open(tp, 'w') as tf:
            # agent_cmd records the FULL per-phase command map — identical across
            # every transcript of the run, so the manifest consistency check holds
            # for cases with different phase sets (gate-02 vs gate-07)
            tf.write(json.dumps({'type': 'runner_start', 'case_id': cid, 'run_id': run_id,
                                 'main_model': a['model'], 'secondary_model': None,
                                 'phases': sorted(prompts[cid]),
                                 'claude_version': claude_version,
                                 'test_mode': bool(os.environ.get('RUNNER_AGENT_CMD')),
                                 'agent_cmd': cmds}) + '\n')
            for ph in PHASES:
                if ph not in prompts[cid]:
                    continue
                fixture = None
                if ph == 'orchestration':
                    fixture = os.path.join(FIXROOT, cid)
                    if not os.path.isdir(fixture):
                        fail('orch sandbox fixture missing: ' + fixture)
                rtext, rc = run_phase(cmds[ph], prompts[cid][ph], tf, ph, a['timeout'], fixture)
                if rc != 0 or rtext is None:
                    # a failed/timeout/result-less phase poisons the whole case:
                    # no draft row — and the scorer independently hard-FAILs the
                    # transcript via the runner_start.phases <-> phase_result check
                    warns.append('%s/%s: agent failed (exit %s%s) — case excluded from draft'
                                 % (cid, ph, rc, '' if rtext is not None else ', no result'))
                    case_ok = False
                res[ph] = rtext
            tf.write(json.dumps({'type': 'runner_end', 'case_id': cid, 'run_id': run_id}) + '\n')
        os.chmod(tp, 0o600)
        if not case_ok:
            continue
        if 'orchestration' in res:
            # execution-tier draft row: violation bits default clean (grader
            # judgments); the scorer audits the trace, not this self-report
            oj, oj_raw = last_json_line(res.get('orchestration'))
            if not isinstance(oj, dict):
                warns.append(cid + ': no orchestration JSON self-report — draft row skipped')
                continue
            results.append({'id': cid, 'dual_chain_violation': False,
                            'unauthorized_side_effect': False, 'done_without_verification': False,
                            'must_missing': [], 'forbid_present': [],
                            'evidence': {'orchestration': oj_raw}})
            continue
        act, act_raw = last_json_line(res.get('activation'))
        rt, rt_raw = last_json_line(res.get('routing'))
        pj, pj_raw = last_json_line(res.get('protocol'))
        if not isinstance(act, dict):
            warns.append(cid + ': no activation JSON — draft row skipped')
            continue
        row = {'id': cid, 'triggered': act.get('triggered'), 'route': (rt or {}).get('route'),
               'clarify': (rt or {}).get('clarify'), 'yield': act.get('yield'),
               'dual_chain_violation': False, 'unauthorized_side_effect': False,
               'done_without_verification': False, 'must_missing': [], 'forbid_present': [],
               'evidence': {'activation': act_raw, 'routing': rt_raw, 'protocol': pj_raw}}
        if isinstance(rt, dict) and isinstance(rt.get('auto'), dict):
            row['auto'] = rt['auto']
        if isinstance(rt, dict) and isinstance(rt.get('auto_entered'), bool):
            row['auto_entered'] = rt['auto_entered']
        results.append(row)
    mf = subprocess.run([sys.executable, MANIFESTER, rd, '--run-id', run_id],
                        capture_output=True, text=True)
    if mf.returncode != 0:
        fail('manifest generation failed: ' + (mf.stderr or mf.stdout)[-400:])
    dp = os.path.join(rd, 'results-draft.jsonl')
    with open(dp, 'w') as f:
        for row in results:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    os.chmod(dp, 0o600)
    print('run dir (private, mode 700): ' + rd)
    print('cases: %d dispatched, %d draft rows' % (len(sel), len(results)))
    for w in warns:
        print('WARN ' + w)
    print('next (draft is NOT scoreable — the scorer rejects results-draft.jsonl):')
    print('  1) grader 对照轨迹复核并修订 draft 的违规位与 must/forbid')
    print('  2) %s %s --grader <姓名>' % (os.path.join(HERE, 'finalize-results.py'), rd))
    print('  3) %s --score %s --tier %s --transcripts %s'
          % (VALIDATOR, os.path.join(rd, 'results-final.jsonl'), a['tier'], rd))
    if len(results) != len(sel):
        print('runner exit: 1 (draft rows %d != selected cases %d — failed phases keep their'
              ' diagnostics in the run dir)' % (len(results), len(sel)))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
