"""Explicit Worker receipt fixtures; no network or provider calls."""
from contracts import RECEIPT_SCHEMA


def model_identity(model):
    return {"receipt_schema":RECEIPT_SCHEMA,"model":model,"requested_model":model,"provider_reported_model":model,"identity_match":True}


def writer_validation(sentences, lang="en", budget=4000, ending=False, station="강남"):
    lengths = [len(sentence) for sentence in sentences]
    cap = 40 if lang == "ko" else 90
    over = sum(length > cap for length in lengths)
    failures = []
    if not sentences: failures.append("empty")
    if len(sentences) > 100: failures.append("too_many_sentences")
    if over: failures.append("sentence_cap")
    if sum(lengths) > budget: failures.append("scene_budget")
    ending_ok = bool(sentences and sentences[-1].endswith(station)) if ending else None
    if ending and not ending_ok: failures.append("station_ending")
    return {"status":"rejected" if failures else "valid","purpose":"story",
            "counting_basis":"trimmed-nonempty-lines/unicode-code-points","language":lang,"text_response":True,
            "sentence_count":len(sentences),"sentences_within_cap":len(sentences)-over,"sentences_over_cap":over,
            "max_sentence_chars":max(lengths,default=0),"total_chars":sum(lengths),"sentence_cap":cap,
            "max_sentence_count":100,"required_sentence_count":None,"budget_chars":budget,
            "scene_budget_ok":sum(lengths)<=budget,"sentence_count_ok":0<len(sentences)<=100,
            "sentence_lengths_ok":over==0,"ending_required":ending,"ending_station_ok":ending_ok,
            "passed":not failures,"failures":failures}
