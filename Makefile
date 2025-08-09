.PHONY: fast run test
fast:
\tpython clipper.py --fast -c segments.yaml
run:
\tpython clipper.py -c segments.yaml
test:
\tbash scripts/ci-selftest.sh
