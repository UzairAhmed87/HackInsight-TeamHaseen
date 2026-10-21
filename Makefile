.PHONY: data test readiness forecast dashboard flow

PYTHON ?= python

# Rebuilds every source (PAQI + U.S. Consulate Karachi) and the cross-source checks.
# First run needs OPENAQ_API_KEY (free at https://explore.openaq.org/register); later runs reuse verified raw files.
data:
	$(PYTHON) -m pipeline.warehouse

test:
	$(PYTHON) -m unittest discover -s tests -v

readiness:
	$(PYTHON) -m pipeline.readiness

forecast:
	$(PYTHON) -m pipeline.forecasting

dashboard:
	$(PYTHON) -m pipeline.dashboard

# Requires: pip install -r requirements-pipeline.txt
flow:
	$(PYTHON) prefect_flow.py
