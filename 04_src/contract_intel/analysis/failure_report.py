"""Markdown failure analysis from saved per-query predictions. Reads predictions + gold for DISPLAY only; it never
feeds anything back to the retriever. Used for the baseline report and, later, for the final error analysis."""
import json
from collections import Counter, defaultdict
from pathlib import Path

DEFS = {
    "hit": "recall@k >= 0.99",
    "partial_span": "right place, but the returned text covers only part of the gold span(s)",
    "ranked_too_low": "gold text is retrieved, but only at rank > k",
    "right_doc_wrong_section": "gold never retrieved in the top 64; the top-1 passage is in the right contract",
    "wrong_document": "gold never retrieved in the top 64; the top-1 passage is in another contract",
    "no_candidates": "the retriever returned nothing",
    "ingestion_failure": "returned text differs from document[start:end] (offset bug)",
    "false_abstention": "answerable query where the gate withheld the answer (end-to-end view)",
    "false_answer": "unanswerable query that still received passages",
    "correct_abstention": "unanswerable query correctly given nothing",
}


def _clip(s: str, n: int = 220) -> str:
    s = " ".join(s.split())
    return s if len(s) <= n else s[:n] + "..."


def load_predictions(path: Path) -> list[dict]:
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def build_report(records: list[dict], metrics: dict, store, title: str, examples_per_label: int = 3) -> str:
    ans = [r for r in records if r["answerable"]]
    un = [r for r in records if not r["answerable"]]
    pk = metrics["primary_k"]
    lines = [f"# {title}", "",
             f"Experiment `{metrics['experiment_id']}` · split **{metrics['split']}** (purpose: {metrics['purpose']}) · "
             f"{len(ans)} answerable and {len(un)} unanswerable queries · primary k = {pk}", ""]

    lines += ["## Headline numbers (ranking view, before the abstention gate)", "", "| k | recall | precision |", "|---|---|---|"]
    for k, v in metrics["retrieval_ranking_view"].items():
        lines.append(f"| {k} | {v['recall']:.4f} | {v['precision']:.4f} |")
    a = metrics["abstention"]
    c = a["confusion"]
    lines += ["", "## Abstention (decision-level; not character metrics)", "",
              f"Threshold {metrics['threshold']:.4f}, calibrated on train answerable queries.", "",
              "| | answered | abstained | total |", "|---|---|---|---|",
              f"| answerable | {c['answerable_answered_TP']} | {c['answerable_abstained_FN']} (**false abstention**) | {a['n_answerable']} |",
              f"| unanswerable | {c['unanswerable_answered_FP']} (**false answer**) | {c['unanswerable_abstained_TN']} (correct abstention) | {a['n_unanswerable']} |",
              "", f"False-abstention rate {a['false_abstention_rate']:.3f} · correct-abstention rate {a['correct_abstention_rate']:.3f} · "
              f"false-answer rate {a['false_answer_rate']:.3f} · AUROC of the confidence signal "
              f"{metrics['confidence_auroc_answerable_vs_unanswerable']:.3f}", ""]

    lines += ["## Failure categories (answerable queries, ranking view)", "", "| label | n | share | meaning |", "|---|---|---|---|"]
    cnt = Counter(r["label"] for r in ans)
    for lab, n in cnt.most_common():
        lines.append(f"| {lab} | {n} | {n / len(ans):.1%} | {DEFS.get(lab, '')} |")
    flagged = [r for r in ans if "ambiguous_ground_truth" in r["flags"]]
    lines += ["", f"Flagged `ambiguous_ground_truth` (gold covers >40% of the contract or <15 chars): **{len(flagged)}** queries.", ""]

    by_cat = defaultdict(lambda: [0, 0])
    for r in un:
        by_cat[r["category"]][0] += 1
        by_cat[r["category"]][1] += r["abstained"]
    lines += ["## Unanswerable queries by category", "", "| category | n | correctly abstained |", "|---|---|---|"]
    lines += [f"| {k} | {v[0]} | {v[1]} |" for k, v in sorted(by_cat.items())]
    lines.append("")

    lines += ["## Reviewable examples", "",
              "Each example shows the question, the gold text (evaluation only) and what the system returned at ranks 1-2. "
              "Offsets are `[start, end)` into the original document.", ""]
    for lab, _ in cnt.most_common():
        if lab == "hit":
            continue
        ex = [r for r in ans if r["label"] == lab]
        lines += [f"### {lab} ({len(ex)})", ""]
        for r in ex[:examples_per_label]:
            g = r["gold_for_evaluation_only"][0]
            gt = store.text(g["doc_id"])[g["start"]:g["end"]]
            lines += [f"- **{r['query_id']}** · {_clip(r['query'].split(';', 1)[-1].strip(), 120)}  ",
                      f"  contract `{g['doc_id'].split('/')[-1][:60]}` · gold {g['start']}-{g['end']}"
                      f" ({len(r['gold_for_evaluation_only'])} span(s)) · first gold overlap at rank {r['found_rank']}  ",
                      f"  gold: “{_clip(gt)}”  "]
            for p in r["passages"][:2]:
                same = "same contract" if p["doc_id"] == g["doc_id"] else "OTHER contract"
                lines.append(f"  rank {p['rank']} ({same}, {p['start']}-{p['end']}, score {p['score']:.2f}): "
                             f"“{_clip(store.text(p['doc_id'])[p['start']:p['end']], 160)}”  ")
            lines.append("")
    fa = [r for r in un if not r["abstained"]]
    lines += [f"### false_answer ({len(fa)} of {len(un)} unanswerable)", ""]
    for r in fa[:4]:
        p = r["passages"][0] if r["passages"] else None
        lines.append(f"- **{r['query_id']}** [{r['category']}] {_clip(r['query'], 160)}  ")
        if p:
            lines.append(f"  top passage (score {p['score']:.2f}): “{_clip(store.text(p['doc_id'])[p['start']:p['end']], 160)}”  ")
    lines += ["", "## Notes", "",
              "- Ground-truth text above is shown for review only; it was never an input to retrieval.",
              "- A `false_answer` means the gate did not withhold; it does not mean the returned text is a wrong clause.", ""]
    return "\n".join(lines)
