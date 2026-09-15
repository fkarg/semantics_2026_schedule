.PHONY: test favourites mobile calendar browser now programme

# Longest workflows first. Use make -j2 test, or name only the affected suites.
test: favourites mobile calendar browser now programme

favourites mobile calendar browser now programme:
	.venv/bin/python -m tests.test_$@
