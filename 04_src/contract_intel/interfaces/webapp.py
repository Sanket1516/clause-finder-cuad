"""Streamlit front end. All retrieval goes through `SearchService` (the same object the CLI uses).

`run_search` is a pure function returning a view model, so request handling is testable without a browser."""
from dataclasses import dataclass, field

from ..application import ApplicationError, SearchService, list_configs
from ..data.loader import MissingDataError
from ..common.config import ConfigError

DISCLAIMER = ("These are candidate passages found by a retrieval system, not legal conclusions. Always read the clause in the "
              "contract itself, and have a qualified person confirm anything that matters.")

EXAMPLES = {
    "Governing law (answerable)": "Consider the Marketing Agreement between Loop Industries, Inc. and Indorama Loop Technologies, LLC "
                                  "for Product Supply and Development; What is the governing law for this contract?",
    "Anti-assignment (answerable)": "Consider the Sponsorship Agreement between R. C. Boyd Enterprises, LLC and Cano Petroleum, Inc. "
                                    "for 'Honey Hole'; Is there an anti-assignment clause in this contract?",
    "Clause absent from the contract (abstains)": "Consider the Amendment No. 3 to Wireless Content License Agreement between Fox Mobile "
                                                  "Entertainment, Inc. and Glu Mobile Inc.; What is the governing law for this contract?",
    "Contract not indexed (known weakness)": "Consider the Master Content Licence Agreement between Aurora Streaming Ltd. and Northwind "
                                             "Studios Inc.; Does this agreement allow Aurora to sublicense the content to a third-party platform?",
}


@dataclass
class View:
    status: str  # "invalid" | "error" | "answered" | "abstained"
    message: str = ""
    detail: str = ""
    passages: list[dict] = field(default_factory=list)
    weak: list[dict] = field(default_factory=list)
    meta: dict = field(default_factory=dict)


def _row(p, store) -> dict:
    return {"rank": p.rank, "doc_id": p.doc_id, "document": p.doc_id.split("/")[-1].removesuffix(".txt"), "start": p.start,
            "end": p.end, "score": round(p.score, 3), "text": p.text,
            "before": store.text(p.doc_id)[max(0, p.start - 300):p.start], "after": store.text(p.doc_id)[p.end:p.end + 300]}


def run_search(svc: SearchService, question: str, k: int) -> View:
    try:
        resp = svc.search(question, k)
    except ApplicationError as e:
        return View("invalid", str(e))
    except (MissingDataError, ConfigError) as e:
        return View("error", f"Configuration or data problem: {e}")
    except Exception as e:  # noqa: BLE001 - never show a traceback to the user
        return View("error", f"Unexpected error ({type(e).__name__}). The question was not answered.", str(e))
    meta = {"experiment_id": resp.experiment_id, "confidence": round(resp.confidence, 3), "threshold": resp.threshold,
            "decision": resp.decision}
    if resp.abstained:
        return View("abstained", "No passage cleared the evidence threshold.",
                    (resp.abstention_reason or "") + " This does not prove that the contract has no such clause.",
                    weak=[_row(p, svc.store) for p in resp.ranked_candidates[:k]], meta=meta)
    return View("answered", f"{len(resp.passages)} passage(s) cleared the evidence threshold.", passages=[_row(p, svc.store) for p in resp.passages],
                meta=meta)


def main() -> None:  # pragma: no cover - exercised through streamlit.testing in the tests
    import os

    import streamlit as st

    st.set_page_config(page_title="Contract Clause Search", layout="wide")
    st.title("Contract Clause Search")
    st.caption("Finds the passages of the indexed contracts that are most likely to answer a question, with their exact location. "
               "It is a retrieval aid, not a legal advisor.")

    @st.cache_resource(show_spinner="Building the index...")
    def get_service(config: str) -> SearchService:
        return SearchService(config)

    configs = list_configs() or ["final"]
    default = os.environ.get("CONTRACT_INTEL_CONFIG", "final")
    with st.sidebar:
        st.header("Settings")
        config = st.selectbox("Retrieval configuration", configs, index=configs.index(default) if default in configs else 0)
        k = st.slider("Number of passages", 1, 10, 5)
        with st.expander("How to read the results", expanded=True):
            st.markdown(
                "- **Passage**: text copied exactly from the contract, with its document and character range `[start, end)`.\n"
                "- **Score**: a relevance score (higher is better). It is not a probability.\n"
                "- **Cleared the threshold**: the best passage scored above a cut-off chosen on development data. "
                "Cleared does not mean correct.\n"
                "- **No sufficient evidence**: nothing cleared the cut-off. This is *not* proof that no clause exists; "
                "the clause may be worded unusually or sit in a document that is not indexed.")
        st.caption(DISCLAIMER)

    st.write("Name the contract and ask about a clause, e.g. *Consider the &lt;contract&gt;; What is the governing law for this contract?*")
    if "q" not in st.session_state:
        st.session_state["q"] = ""
    cols = st.columns(len(EXAMPLES))
    for col, (label, text) in zip(cols, EXAMPLES.items()):
        if col.button(label, use_container_width=True):
            st.session_state["q"] = text
    question = st.text_area("Question", key="q", height=100, placeholder="Consider the <contract>; ...")
    go = st.button("Search", type="primary")

    if go:
        try:
            svc = get_service(config)
        except Exception as e:  # noqa: BLE001
            st.error(f"Could not start the search engine: {e}")
            return
        view = run_search(svc, question, k)
        if view.status == "invalid":
            st.warning(view.message)
        elif view.status == "error":
            st.error(view.message)
            if view.detail:
                with st.expander("Technical detail"):
                    st.code(view.detail)
        else:
            if view.status == "answered":
                st.success(view.message)
                st.caption(DISCLAIMER)
                for p in view.passages:
                    with st.container(border=True):
                        st.markdown(f"**#{p['rank']} · {p['document']}** — characters {p['start']}–{p['end']} · score {p['score']}")
                        st.text(p["text"])
                        with st.expander("Show surrounding text"):
                            st.text(p["before"] + "[[" + p["text"] + "]]" + p["after"])
            else:
                st.warning("No sufficient evidence found")
                st.write(view.message)
                st.info(view.detail)
                if view.weak:
                    with st.expander("Best passages found (below the threshold — NOT sufficient evidence)"):
                        for p in view.weak:
                            st.markdown(f"**#{p['rank']} · {p['document']}** — characters {p['start']}–{p['end']} · score {p['score']}")
                            st.text(p["text"][:600])
            st.caption(f"configuration {view.meta['experiment_id']} · confidence {view.meta['confidence']} · threshold {view.meta['threshold']}")
