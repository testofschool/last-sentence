#!/usr/bin/env python3
"""Guarded, controlled Korean Super/Ultra feedback collector.

Default: fetch the public catalog and print a plan; never infer. Execution needs
--execute, a fresh saved plan, --ack-cost-cap-usd <= .05, a mode-600 Worker
session file, and an advertised protected Worker. No vendor key bytes are read.
A key-ready marker observes local file presence, never signup/key creation.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
import datetime as dt
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

CATALOG_URL = 'https://tokenfactory.nebius.com/api/public/models_info'
SUPER = 'nvidia/nemotron-3-super-120b-a12b'
ULTRA = 'nvidia/Nemotron-3-Ultra-550b-a55b'
MODELS = (SUPER, ULTRA)
PURPOSE = 'feedback-korean-compare'
MAX_INPUT, MAX_OUTPUT, SENTENCES, SENTENCE_CAP, BUDGET = 16384, 180, 3, 40, 120
MAX_LOCAL_CAP = Decimal('.05')
PLAN_TTL_S = 300
SCENE = '서울 지하철 빈 좌석에서 노란 봉투를 발견한 사람이 봉투 속 손그림 지도를 펼치는 장면입니다. 인물과 장소를 늘리지 말고 이 장면만 짧은 한국어 이야기로 쓰세요.'
VENDOR_PATHS = tuple(Path.home() / name for name in ('.nebius_key', '.seoul_rt_key', '.tavily_key'))

class FeedbackError(ValueError): pass
class TransportError(FeedbackError): pass

@dataclass
class Reply:
    status: int
    data: dict | list
    headers: dict
    elapsed_ms: float

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise TransportError('HTTP redirect refused; credentials were not forwarded')

class HttpTransport:
    is_mock = False
    def __init__(self):
        context = ssl.create_default_context()
        if Path('/etc/ssl/cert.pem').is_file(): context.load_verify_locations('/etc/ssl/cert.pem')
        self.opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=context))
    def __call__(self, method, url, body=None, token=None, timeout=15):
        headers = {'accept': 'application/json', 'User-Agent': 'Last-Sentence-Evaluation/0.1'}
        if token: headers['authorization'] = 'Bearer ' + token
        raw = None
        if body is not None:
            raw = json.dumps(body, ensure_ascii=False, allow_nan=False).encode()
            headers['content-type'] = 'application/json'
        request = urllib.request.Request(url, data=raw, headers=headers, method=method)
        started = time.monotonic()
        try:
            try: response = self.opener.open(request, timeout=timeout)
            except urllib.error.HTTPError as error: response = error
            with response:
                content = response.read(2_000_001)
                if len(content) > 2_000_000: raise TransportError('response size limit exceeded')
                try: data = json.loads(content)
                except (ValueError, UnicodeError): raise TransportError('response was not JSON')
                selected = {k.lower(): v for k, v in response.headers.items()
                            if k.lower().startswith('x-ratelimit-') or k.lower() in ('retry-after', 'content-type')}
                return Reply(response.code, data, selected, (time.monotonic() - started) * 1000)
        except FeedbackError: raise
        except (OSError, urllib.error.URLError, TimeoutError):
            raise TransportError('network request failed or timed out; dispatch outcome may be unknown')


def utc_now(): return dt.datetime.now(dt.timezone.utc)
def iso(value): return value.astimezone(dt.timezone.utc).isoformat()
def timestamp(value):
    try:
        parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None: raise ValueError()
        return parsed.astimezone(dt.timezone.utc)
    except (AttributeError, ValueError, TypeError): raise FeedbackError('invalid timezone-aware timestamp')

def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise FeedbackError('a finite nonnegative numeric value is required')
    try: result = Decimal(str(value))
    except InvalidOperation: raise FeedbackError('invalid numeric value')
    if not result.is_finite() or result < 0: raise FeedbackError('invalid numeric value')
    return result

def integer(value): return isinstance(value, int) and not isinstance(value, bool) and value >= 0

def guard_nonvendor(path):
    path = Path(path).expanduser()
    if path.name in {p.name for p in VENDOR_PATHS}:
        raise FeedbackError('vendor credential files cannot be read as collector inputs')
    try: info = path.lstat()
    except FileNotFoundError: info = None
    if info and stat.S_ISLNK(info.st_mode): raise FeedbackError('symlink inputs/outputs are refused')
    for vendor in VENDOR_PATHS:
        if path.absolute() == vendor.absolute(): raise FeedbackError('vendor credential path refused')
        try: vendor_info = vendor.lstat()
        except FileNotFoundError: continue
        if info and (info.st_dev, info.st_ino) == (vendor_info.st_dev, vendor_info.st_ino):
            raise FeedbackError('vendor credential hard-link refused')
    return path

def safe_read(path, limit, protected=False):
    path = guard_nonvendor(path)
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
    try: descriptor = os.open(path, flags)
    except OSError: raise FeedbackError('required input file is unavailable')
    with os.fdopen(descriptor, 'rb') as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit: raise FeedbackError('input must be a bounded regular file')
        if protected and (stat.S_IMODE(info.st_mode) != 0o600 or (hasattr(os, 'getuid') and info.st_uid != os.getuid())):
            raise FeedbackError('Worker session/marker file must be owned by this user with mode 600')
        # Recheck opened inode, closing the lstat/open race without reading a key.
        for vendor in VENDOR_PATHS:
            try: candidate = vendor.lstat()
            except FileNotFoundError: continue
            if (candidate.st_dev, candidate.st_ino) == (info.st_dev, info.st_ino):
                raise FeedbackError('opened file is a vendor credential')
        data = handle.read(limit + 1)
        if len(data) > limit: raise FeedbackError('input file size limit exceeded')
        return data

def new_output(path):
    path = guard_nonvendor(path)
    if path.exists(): raise FeedbackError('output already exists; no overwrite is permitted')
    try: descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    except OSError: raise FeedbackError('cannot exclusively create output')
    return os.fdopen(descriptor, 'w+', encoding='utf-8')

def read_json(path, protected=False):
    try: value = json.loads(safe_read(path, 200_000, protected).decode('utf-8'))
    except FeedbackError: raise
    except (ValueError, UnicodeError): raise FeedbackError('input is not valid UTF-8 JSON')
    if not isinstance(value, dict): raise FeedbackError('JSON input must be an object')
    return value

def worker_url(value):
    try:
        parsed = urllib.parse.urlsplit(value)
        if parsed.username or parsed.password or parsed.query or parsed.fragment or not parsed.hostname:
            raise ValueError()
        if parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1', '::1')):
            raise ValueError()
        if '..' in urllib.parse.unquote(parsed.path).split('/'): raise ValueError()
        return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip('/'), '', ''))
    except (ValueError, TypeError): raise FeedbackError('Worker URL must be HTTPS, or HTTP loopback, without credentials/query/fragment')

def rates_from_catalog(data):
    rows = data if isinstance(data, list) else data.get('models', data.get('data', [])) if isinstance(data, dict) else []
    if not isinstance(rows, list): raise FeedbackError('catalog has an unsupported shape')
    rates = {}
    for row in rows:
        if not isinstance(row, dict) or row.get('status') not in (None, 'active'): continue
        flavors = row.get('flavors', [row])
        if not isinstance(flavors, list): continue
        for entry in flavors:
            if not isinstance(entry, dict): continue
            model = entry.get('model_id', entry.get('id', entry.get('name')))
            if model not in MODELS: continue
            pair = (number(entry.get('input_price_per_million_tokens')), number(entry.get('output_price_per_million_tokens')))
            if model in rates and rates[model] != pair: raise FeedbackError('ambiguous duplicate model pricing')
            rates[model] = pair
    if set(rates) != set(MODELS): raise FeedbackError('fresh catalog is missing a required comparison model')
    return rates

def encoded_rates(rates):
    return {model: {'input_price_per_million_tokens': float(pair[0]), 'output_price_per_million_tokens': float(pair[1])}
            for model, pair in rates.items()}

def decode_rates(data):
    if not isinstance(data, dict) or set(data) != set(MODELS): raise FeedbackError('plan must price exactly the two approved models')
    return {model: (number(data[model].get('input_price_per_million_tokens')), number(data[model].get('output_price_per_million_tokens'))) for model in MODELS}

def cost_bound(rates, model): return (MAX_INPUT * rates[model][0] + MAX_OUTPUT * rates[model][1]) / Decimal(1_000_000)

def fresh_catalog(transport, now, timeout=15):
    response = transport('GET', CATALOG_URL, timeout=timeout)
    if response.status != 200: raise FeedbackError('fresh public catalog request failed')
    rates = rates_from_catalog(response.data)
    digest = hashlib.sha256(json.dumps(response.data, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    return rates, {'source_url': CATALOG_URL, 'fetched_at': iso(now()), 'canonical_json_sha256': digest}

def common_body(): return {'purpose': PURPOSE, 'lang': 'ko', 'sentence_count': 3, 'budget_chars': 120, 'scene': SCENE}
def common_hash(): return hashlib.sha256(json.dumps(common_body(), sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def make_plan(transport=None, now=utc_now, worker=None):
    injected = transport is not None
    transport = transport or HttpTransport()
    rates, catalog = fresh_catalog(transport, now)
    created = now()
    return {'schema': 'last-sentence/korean-feedback-plan-v1', 'evidence_kind': 'mocked-plan' if injected else 'plan-only-no-inference',
            'created_at': iso(created), 'expires_at': iso(created + dt.timedelta(seconds=PLAN_TTL_S)),
            'catalog': catalog, 'prices': encoded_rates(rates), 'worker_url': worker_url(worker) if worker else None,
            'common_request': common_body(), 'common_request_sha256': common_hash(), 'model_order': list(MODELS),
            'limits': {'max_input_tokens_per_completion': MAX_INPUT, 'max_output_tokens_per_completion': MAX_OUTPUT,
                       'completion_attempts': 2, 'sentence_count': 3, 'sentence_cap': 40, 'budget_chars': 120,
                       'maximum_local_ack_cap_usd': float(MAX_LOCAL_CAP)},
            'cost_bound_by_model_usd': {model: float(cost_bound(rates, model)) for model in MODELS},
            'worst_case_usd': float(sum(cost_bound(rates, model) for model in MODELS)),
            'allowed_under_small_cap': sum(cost_bound(rates, model) for model in MODELS) <= MAX_LOCAL_CAP,
            'inference_calls_made': 0, 'korean_quality': 'UNMEASURED-human-review-required'}

def mark_key_ready(output, key_file=None, now=utc_now):
    # Presence observation only: do not open/read the vendor file or use its mtime.
    key_file = Path(key_file) if key_file else Path.home() / '.nebius_key'
    try: info = key_file.lstat()
    except FileNotFoundError: raise FeedbackError('key file is absent; no readiness marker created')
    if not stat.S_ISREG(info.st_mode) or info.st_size <= 0: raise FeedbackError('key readiness needs a nonempty regular file')
    marker = {'schema': 'last-sentence/key-ready-observation-v1', 'observed_at': iso(now()), 'key_file_name': key_file.name,
              'observation': 'local-file-presence-only', 'key_bytes_read': False,
              'does_not_establish': ['key creation time', 'account signup time', 'actual Worker credential identity']}
    with new_output(output) as handle: json.dump(marker, handle, ensure_ascii=False, indent=2); handle.write('\n')
    return marker

def ready_marker(path, now):
    if not path: return None
    marker = read_json(path, protected=True)
    if marker.get('schema') != 'last-sentence/key-ready-observation-v1' or marker.get('observation') != 'local-file-presence-only' or marker.get('key_bytes_read') is not False:
        raise FeedbackError('key-ready marker has an unsupported provenance')
    observed = timestamp(marker.get('observed_at'))
    if observed > now() + dt.timedelta(seconds=5): raise FeedbackError('key-ready marker is in the future')
    return marker

def scrub(value, token):
    if isinstance(value, str): return value.replace(token, '[REDACTED_SESSION_TOKEN]') if token else value
    if isinstance(value, list): return [scrub(v, token) for v in value]
    if isinstance(value, dict): return {k: scrub(v, token) for k, v in value.items()}
    return value

def checkpoint(handle, document, token):
    content = json.dumps(scrub(document, token), ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    handle.seek(0); handle.truncate(); handle.write(content); handle.flush(); os.fsync(handle.fileno())

def check_status(response, models_left, reserve_left):
    if response.status != 200 or not isinstance(response.data, dict): raise FeedbackError('Worker status is unavailable')
    status = response.data
    if status.get('inference_enabled') is not True: raise FeedbackError('protected Worker inference is not enabled')
    if status.get('receipt_schema') != 'last-sentence/receipt-v2': raise FeedbackError('Worker receipt schema version is unsupported')
    for flag in ('feedback_korean_compare_supported', 'receipt_provenance_supported', 'writer_validation_supported', 'expected_pricing_supported'):
        if status.get(flag) is not True: raise FeedbackError('Worker lacks required comparison/pricing/receipt capability: ' + flag)
    limits = status.get('feedback_probe_limits', {})
    expected = {'max_input_token_bound': MAX_INPUT, 'max_output_tokens': MAX_OUTPUT, 'sentence_count': 3, 'sentence_cap': 40, 'budget_chars': 120}
    if any(limits.get(key) != value for key, value in expected.items()) or set(limits.get('allowed_models', [])) != set(MODELS):
        raise FeedbackError('Worker controlled-probe envelope does not match the acknowledged plan')
    if status.get('max_input_token_bound') != MAX_INPUT: raise FeedbackError('Worker input envelope is not the planned bound')
    quota = status.get('limits', {})
    available, reserved = number(quota.get('reservation_budget_usd')), number(quota.get('reserved_usd'))
    calls = quota.get('completion_calls_remaining')
    if not integer(calls) or calls < models_left or not Decimal(0) <= reserved <= available <= Decimal(3) or available - reserved < reserve_left:
        raise FeedbackError('authenticated shared Worker budget or completion quota is insufficient')
    return {key: status[key] for key in ('receipt_schema', 'limits', 'feedback_probe_limits', 'expected_pricing_supported', 'receipt_provenance_supported', 'writer_validation_supported', 'feedback_korean_compare_supported')}

def receipt_check(data, model, rates):
    if not isinstance(data, dict): raise FeedbackError('Worker response is not a receipt object')
    calls = data.get('calls')
    if not isinstance(calls, list) or len(calls) != 1 or not isinstance(calls[0], dict): raise FeedbackError('exactly one completion receipt is required')
    call = calls[0]
    for receipt in (data, call):
        if receipt.get('receipt_schema') != 'last-sentence/receipt-v2': raise FeedbackError('completion receipt schema version is unsupported')
        if receipt.get('model') != model: raise FeedbackError('compatibility model disagrees with the requested identity')
        if receipt.get('requested_model') != model or receipt.get('provider_reported_model') != model or receipt.get('identity_match') is not True:
            raise FeedbackError('provider identity is missing or mismatched; actual cost stays unknown')
    usage = call.get('usage')
    if not isinstance(usage, dict) or not integer(usage.get('prompt_tokens')) or not integer(usage.get('completion_tokens')):
        raise FeedbackError('verified token usage is unavailable; actual cost stays unknown')
    if not integer(usage.get('total_tokens')) or usage['total_tokens'] != usage['prompt_tokens'] + usage['completion_tokens']: raise FeedbackError('total usage tokens are missing or inconsistent')
    if usage['prompt_tokens'] > MAX_INPUT or usage['completion_tokens'] > MAX_OUTPUT: raise FeedbackError('provider usage exceeded the acknowledged envelope')
    if data.get('usage') != usage: raise FeedbackError('aggregate and per-call token usage disagree')
    bound = call.get('input_token_bound')
    if not integer(bound) or bound < 1 or bound > MAX_INPUT: raise FeedbackError('receipt lacks the enforced input bound')
    pricing = call.get('pricing', {})
    if pricing.get('fresh_for_dispatch') is not True or pricing.get('acknowledged') is not True:
        raise FeedbackError('predispatch acknowledged pricing was not confirmed')
    if (number(pricing.get('input_price_per_million_tokens')), number(pricing.get('output_price_per_million_tokens'))) != rates[model]:
        raise FeedbackError('receipt pricing differs from the acknowledged catalog')
    estimate = (usage['prompt_tokens'] * rates[model][0] + usage['completion_tokens'] * rates[model][1]) / Decimal(1_000_000)
    for receipt in (data, call):
        if receipt.get('cost_usd') is None or abs(number(receipt.get('cost_usd')) - estimate) > Decimal('0.0000000001'):
            raise FeedbackError('verified usage-based cost is missing or inconsistent')
        if receipt.get('requested_rate_cost_estimate_usd') is None or abs(number(receipt.get('requested_rate_cost_estimate_usd'))-estimate)>Decimal('0.0000000001'): raise FeedbackError('requested-rate cost estimate is missing or inconsistent')
    return estimate, call

def inspect_validation_summary(validation, rejected=False):
    """Validate Worker-reported counters without pretending rejected text exists."""
    if not isinstance(validation,dict) or validation.get('purpose')!=PURPOSE or validation.get('language')!='ko' or validation.get('counting_basis')!='trimmed-nonempty-lines/unicode-code-points' or validation.get('required_sentence_count')!=3 or validation.get('max_sentence_count')!=3 or validation.get('sentence_cap')!=40 or validation.get('budget_chars')!=120 or validation.get('ending_required') is not False or validation.get('ending_station_ok') is not None:
        raise FeedbackError('controlled-probe validation summary contract is unavailable')
    if validation.get('text_response') is not True:
        raise FeedbackError('no inspected text counters are available for the denominator')
    keys=('sentence_count','sentences_within_cap','sentences_over_cap','max_sentence_chars','total_chars')
    counts={key:validation.get(key) for key in keys}
    if any(not integer(value) or value>2_000_000 for value in counts.values()): raise FeedbackError('validation counters are missing or unbounded')
    n,within,over,maximum,total=(counts[key] for key in keys)
    if within+over!=n or (n==0 and (maximum!=0 or total!=0)) or (n>0 and not 1<=maximum<=total<=n*maximum) or (n>0 and total<n) or (over==0 and maximum>40) or (over>0 and maximum<=40):
        raise FeedbackError('validation counters are inconsistent')
    flags={'scene_budget_ok':total<=120,'sentence_count_ok':n==3,'sentence_lengths_ok':over==0}
    if any(validation.get(key) is not value for key,value in flags.items()): raise FeedbackError('validation booleans disagree with counters')
    failures=[]
    if n==0: failures.append('empty')
    if n!=3: failures.append('exact_sentence_count')
    if over: failures.append('sentence_cap')
    if total>120: failures.append('scene_budget')
    if validation.get('failures')!=failures or validation.get('passed') is not (not failures) or validation.get('status')!=('rejected' if failures else 'valid'):
        raise FeedbackError('validation verdict disagrees with counters')
    if rejected and not failures: raise FeedbackError('HTTP-error output has no verified rejection counters')
    if not rejected and failures: raise FeedbackError('successful output has rejected validation counters')
    return counts

def inspect_success(data, call):
    lines = data.get('sentences')
    if data.get('purpose') != PURPOSE or not isinstance(lines, list) or len(lines) != 3 or any(not isinstance(line, str) or not line.strip() or line != line.strip() or '\n' in line or '\r' in line for line in lines):
        raise FeedbackError('successful probe must contain exactly three nonempty trimmed lines')
    lengths = [len(line) for line in lines]
    observed = {'sentence_count': 3, 'sentences_within_cap': sum(n <= 40 for n in lengths), 'sentences_over_cap': sum(n > 40 for n in lengths),
                'max_sentence_chars': max(lengths), 'total_chars': sum(lengths)}
    validation = call.get('writer_validation', {})
    inspect_validation_summary(validation)
    if validation.get('status') != 'valid' or validation.get('language') != 'ko' or validation.get('text_response') is not True or any(validation.get(key) is not True for key in ('scene_budget_ok','sentence_count_ok','sentence_lengths_ok')) or validation.get('failures') != [] or validation.get('purpose') != PURPOSE or validation.get('required_sentence_count') != 3 or validation.get('max_sentence_count') != 3 or validation.get('sentence_cap') != 40 or validation.get('budget_chars') != 120 or validation.get('passed') is not True:
        raise FeedbackError('Worker three-line validation receipt is unavailable')
    if any(validation.get(key) != value for key, value in observed.items()) or observed['sentences_over_cap'] or observed['total_chars'] > 120:
        raise FeedbackError('Worker validation disagrees with independently counted output')
    return observed

def preserve_response(data):
    if not isinstance(data, dict): return {'error': 'non-object Worker response'}
    keys = ('receipt_schema', 'mode', 'purpose', 'model', 'requested_model', 'provider_reported_model', 'identity_match', 'usage', 'cost_usd',
            'requested_rate_cost_estimate_usd', 'latency_ms', 'calls', 'sentences', 'sentence_cap', 'char_count', 'error', 'message', 'reason')
    return {key: data[key] for key in keys if key in data}


def execute(plan, output, worker, session_file, ack_cost, *, execute_flag=False, marker_path=None,
            transport=None, now=utc_now, clock=time.monotonic, max_runtime_s=180):
    if not execute_flag: raise FeedbackError('--execute is required before any controlled completion')
    if not 30 <= max_runtime_s <= 300: raise FeedbackError('runtime must be bounded to 30–300 seconds')
    mock = transport is not None
    transport = transport or HttpTransport()
    base = worker_url(worker)
    if plan.get('schema') != 'last-sentence/korean-feedback-plan-v1' or plan.get('common_request') != common_body() or plan.get('common_request_sha256') != common_hash() or plan.get('model_order') != list(MODELS):
        raise FeedbackError('the saved controlled scene/protocol plan is invalid')
    current = now();created=timestamp(plan.get('created_at'));expires=timestamp(plan.get('expires_at'));fetched=timestamp(plan.get('catalog',{}).get('fetched_at'))
    if created>current+dt.timedelta(seconds=5) or fetched>current+dt.timedelta(seconds=5) or (current-created).total_seconds()>PLAN_TTL_S or expires!=created+dt.timedelta(seconds=PLAN_TTL_S) or expires<current or (current-fetched).total_seconds()>PLAN_TTL_S:
        raise FeedbackError('saved plan/catalog is stale or future-dated; create a fresh plan')
    if plan.get('catalog',{}).get('source_url')!=CATALOG_URL: raise FeedbackError('plan catalog source is not the primary endpoint')
    if not mock and plan.get('evidence_kind')!='plan-only-no-inference': raise FeedbackError('a mocked plan cannot authorize an actual probe')
    if plan.get('limits')!={'max_input_tokens_per_completion':MAX_INPUT,'max_output_tokens_per_completion':MAX_OUTPUT,'completion_attempts':2,'sentence_count':3,'sentence_cap':40,'budget_chars':120,'maximum_local_ack_cap_usd':float(MAX_LOCAL_CAP)}: raise FeedbackError('saved plan envelope was altered')
    if plan.get('worker_url') and worker_url(plan['worker_url']) != base: raise FeedbackError('Worker differs from the saved plan')
    rates = decode_rates(plan.get('prices'))
    upper = sum(cost_bound(rates, model) for model in MODELS)
    if abs(number(plan.get('worst_case_usd'))-upper)>Decimal('0.0000000001') or any(abs(number(plan.get('cost_bound_by_model_usd',{}).get(model))-cost_bound(rates,model))>Decimal('0.0000000001') for model in MODELS): raise FeedbackError('saved cost bound was altered')
    try: cap = Decimal(str(ack_cost))
    except InvalidOperation: raise FeedbackError('explicit numeric --ack-cost-cap-usd is required')
    if not cap.is_finite() or not 0 < cap <= MAX_LOCAL_CAP or upper > cap: raise FeedbackError('the two-call bound exceeds the acknowledged small local cap')
    guard_nonvendor(output)
    if Path(output).exists(): raise FeedbackError('output already exists; no request will be made')
    token = safe_read(session_file, 4096, protected=True).decode('utf-8').strip()
    if not token or len(token) > 512 or any(ord(char) < 33 or ord(char) == 127 for char in token): raise FeedbackError('invalid Worker session token file')
    marker = ready_marker(marker_path, now)
    deadline = clock() + max_runtime_s
    document = {'schema': 'last-sentence/korean-feedback-v1', 'status': 'running', 'evidence_kind': 'mocked-feedback-probe' if mock else 'controlled-worker-feedback-probe',
                'started_at': iso(now()), 'worker_url':base,'max_runtime_s':max_runtime_s,'plan': plan, 'local_ack_cap_usd': float(cap), 'reserved_local_bound_usd': 0,
                'worker_write_attempts': 0, 'rows': [], 'price_checks': [], 'errors': [], 'korean_quality': 'UNMEASURED-human-review-required',
                'cost_basis': 'usage estimate at freshly acknowledged exact requested/provider-matched model rates; not a billing receipt',
                'onboarding': {'status': 'UNMEASURED', 'reason': 'no genuine local observed-readiness marker and verified first reply yet; key creation is never inferred'}}
    def remaining(maximum):
        left = deadline - clock()
        if left <= 0: raise FeedbackError('bounded collector runtime exhausted; no retry')
        return min(maximum, left)
    first_verified_at = None
    with new_output(output) as handle:
        checkpoint(handle, document, token)
        try:
            for index, model in enumerate(MODELS):
                row = {'requested_model': model, 'provider_reported_model': None, 'identity_match': False, 'status': 'not_dispatched',
                       'common_request_sha256': common_hash(), 'cost_usd': None, 'validation_observed': None}
                document['rows'].append(row)
                actual_rates, catalog = fresh_catalog(transport, now, remaining(15))
                document['price_checks'].append({**catalog, 'unchanged': actual_rates == rates})
                if actual_rates != rates: raise FeedbackError('fresh catalog prices changed; no further completion dispatched')
                future_bound = sum(cost_bound(rates, item) for item in MODELS[index:])
                status = transport('GET', base + '/api/status', token=token, timeout=remaining(25))
                row['worker_gate'] = check_status(status, len(MODELS) - index, future_bound)
                row['status'] = 'dispatching'; row['dispatched_at'] = iso(now())
                row['reserved_bound_usd'] = float(cost_bound(rates, model))
                document['reserved_local_bound_usd'] += row['reserved_bound_usd']
                document['worker_write_attempts'] += 1
                checkpoint(handle, document, token)
                body = {**common_body(), 'feedback_model': model, 'expected_pricing': {'model': model, **encoded_rates(rates)[model]}}
                try: response = transport('POST', base + '/api/write', body=body, token=token, timeout=remaining(45))
                except Exception as error:
                    row.update(status='unknown_outcome', error=type(error).__name__ + ': ' + str(error), cost_usd=None)
                    raise FeedbackError('completion outcome/cost is unknown; second call and automatic retries are refused')
                row.update(http_status=response.status, receipt=preserve_response(response.data), http_headers=response.headers,
                           client_latency_ms=response.elapsed_ms, received_at=iso(now()))
                if response.status!=200 and 'sentences' in row['receipt']:
                    row['receipt'].pop('sentences');row['rejected_text_discarded']=True
                row['provider_reported_model'] = response.data.get('provider_reported_model') if isinstance(response.data, dict) else None
                estimate, call = receipt_check(response.data, model, rates)
                if first_verified_at is None: first_verified_at = now()
                row.update(identity_match=True, cost_usd=float(estimate), writer_validation=call.get('writer_validation'),
                           provider_rate_limit_headers=call.get('rate_limit_headers', {}))
                if response.status == 200:
                    row['validation_observed'] = inspect_success(response.data, call)
                    row.update(validation_countable=True,validation_summary_status='independent-success-text',validation_denominator_excluded=False)
                    row['sentences'] = response.data['sentences']; row['status'] = 'success'
                else:
                    row['status'] = 'rejected'; row['error'] = response.data.get('message', response.data.get('error', 'Worker rejected this model output'))
                    try:
                        row['validation_summary']=inspect_validation_summary(call.get('writer_validation'),rejected=True)
                        row.update(validation_countable=True,validation_summary_status='verified-Worker-rejection-summary',validation_denominator_excluded=False)
                    except FeedbackError as validation_error:
                        row.update(validation_countable=False,validation_summary_status='unavailable',validation_denominator_excluded=True,validation_summary_error=str(validation_error))
                checkpoint(handle, document, token)
            document['status'] = 'complete' if all(row['status'] == 'success' for row in document['rows']) else 'completed-with-rejected-output'
        except Exception as error:
            document['status'] = 'aborted'; document['errors'].append(type(error).__name__ + ': ' + str(error))
            if document['rows'] and document['rows'][-1]['status'] == 'dispatching':
                failed=document['rows'][-1];failed['status']='receipt-unverified'
                if isinstance(failed.get('receipt'),dict) and 'sentences' in failed['receipt']: failed['receipt'].pop('sentences');failed['unverified_text_discarded']=True
        for model in MODELS:
            if not any(row['requested_model'] == model for row in document['rows']): document['rows'].append({'requested_model': model, 'status': 'skipped', 'reason': 'previous gate/outcome stopped the controlled comparison', 'cost_usd': None})
        attempted = [row for row in document['rows'] if 'dispatched_at' in row]
        document['known_cost_subtotal_usd'] = sum(row['cost_usd'] for row in attempted if row.get('cost_usd') is not None)
        document['usage_cost_estimate_usd'] = None if any(row.get('cost_usd') is None for row in attempted) else document['known_cost_subtotal_usd']
        document['provider_completion_receipts']=sum(len(row.get('receipt',{}).get('calls',[])) for row in attempted if isinstance(row.get('receipt',{}).get('calls'),list))
        document['provider_attempts_unknown']=any(row.get('status')=='unknown_outcome' for row in attempted)
        document['inference_automatically_retried']=False
        if marker and first_verified_at and not mock and first_verified_at>=timestamp(marker['observed_at']):
            interval = (first_verified_at - timestamp(marker['observed_at'])).total_seconds()
            document['onboarding'] = {'status': 'MEASURED_LOCAL_OBSERVED_INTERVAL', 'metric': 'local-file-readiness-observation-to-first-verified-Worker-reply',
                                      'seconds': interval, 'minutes': interval / 60, 'marker': marker,
                                      'does_not_measure': 'account signup, key creation time, or the exact server credential identity'}
        document['finished_at'] = iso(now()); checkpoint(handle, document, token)
    return scrub(document, token)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='new JSON path; existing files are never overwritten')
    parser.add_argument('--worker-url')
    parser.add_argument('--plan', type=Path, help='fresh JSON produced by default plan mode')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--ack-cost-cap-usd', help='explicit local cap, at most 0.05 USD; two-call bound must fit')
    parser.add_argument('--session-token-file', type=Path, help='owned mode-600 Worker session token; never a vendor key')
    parser.add_argument('--max-runtime-s', type=float, default=180)
    parser.add_argument('--key-ready-marker', type=Path)
    parser.add_argument('--mark-key-ready', type=Path, help='explicitly write a new local presence-observation marker and exit')
    parser.add_argument('--key-file', type=Path, help='presence-only key path for --mark-key-ready; bytes/mtime are never read')
    args = parser.parse_args(argv)
    try:
        if args.mark_key_ready:
            if args.execute or args.plan or args.session_token_file: raise FeedbackError('readiness marking is a separate presence-only operation')
            result = mark_key_ready(args.mark_key_ready, args.key_file)
        elif args.execute:
            if not all((args.plan, args.output, args.worker_url, args.session_token_file, args.ack_cost_cap_usd)):
                raise FeedbackError('execution requires --plan, --output, --worker-url, --session-token-file and --ack-cost-cap-usd')
            result = execute(read_json(args.plan), args.output, args.worker_url, args.session_token_file, args.ack_cost_cap_usd,
                             execute_flag=True, marker_path=args.key_ready_marker, max_runtime_s=args.max_runtime_s)
        else:
            if args.plan or args.session_token_file or args.ack_cost_cap_usd or args.key_ready_marker or args.key_file:
                raise FeedbackError('execution inputs need --execute; plan mode does not read a token or readiness file')
            result = make_plan(worker=args.worker_url)
            if args.output:
                with new_output(args.output) as handle: json.dump(result, handle, ensure_ascii=False, indent=2, allow_nan=False); handle.write('\n')
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0 if result.get('status') not in ('aborted', 'completed-with-rejected-output') else 2
    except (FeedbackError, OSError, UnicodeError) as error:
        print(json.dumps({'error': str(error), 'inference_automatically_retried': False}), file=sys.stderr)
        return 2

if __name__ == '__main__': raise SystemExit(main())
