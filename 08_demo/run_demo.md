# Running the demo

All commands run from the repository root. Python 3.10+ (developed on 3.11.9).

## One-time setup
```bash
pip install pydantic pyyaml numpy typer huggingface_hub streamlit pytest   # or: pip install -e ".[dev,web]"
python 02_data/download_data.py      # ~1 min; fetches cuad.json + the 29 referenced contracts (6.5 MB), verifies checksums
python 02_data/prepare_dataset.py    # manifests
```
The selectable configurations are in `03_experiments/configs/` (`baseline`, `final`). `final` is the configuration selected on train
by the improvement loop; a config with a null threshold needs `evaluate --split train` first (it freezes the calibrated threshold).

If you run from a different directory, set `PYTHONPATH=04_src`, or use the entry scripts below.

## CLI
```bash
python 04_src/cli.py configs
python 04_src/cli.py search "Consider the Sponsorship Agreement between R. C. Boyd Enterprises, LLC and Cano Petroleum, Inc. for 'Honey Hole'; Is there an anti-assignment clause in this contract?" -k 3
python 04_src/cli.py search "<question>" --config final --json --save result.json
python 04_src/cli.py search "<question>" --show-weak        # when it abstains, also list the weak candidates (labelled insufficient)
```
Exit codes: `0` passages returned · `10` abstained (not an error) · `2` invalid input · `3` missing data / unknown or uncalibrated
configuration · `4` unexpected error.

## Web app
```bash
streamlit run 04_src/web_app.py --server.address localhost
```
Open http://localhost:8501. Use `--server.address localhost` (Streamlit otherwise listens on all network interfaces); the corpus here
is public, but the habit matters for confidential contracts. Click an example button, then **Search**. Use the sidebar to pick the
configuration and the number of passages.

## Reading the output
- `chars a-b` is the half-open character range in the original contract text; "Show surrounding text" shows context with the passage
  in `[[ ]]`.
- *Cleared the threshold* means the best score passed a cut-off picked on development data. It does not mean the passage is right.
- *No sufficient evidence* does not mean the contract lacks the clause.

## Tests
```bash
pytest          # 168 tests in ~8 s; data-dependent tests skip if the data was not downloaded
```
