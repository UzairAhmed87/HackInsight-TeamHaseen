.PHONY: data test readiness forecast dashboard

PYTHON ?= python

data:
	$(PYTHON) -m pipeline.run

test:
	$(PYTHON) -m unittest discover -s tests -v

readiness:
	$(PYTHON) -m pipeline.readiness

forecast:
	$(PYTHON) -m pipeline.forecasting

dashboard:
	$(PYTHON) -m pipeline.dashboard
