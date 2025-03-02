.PHONY: test run serve clean

test:
	python -m unittest discover -s tests

run:
	python -m vibe.main --generate --prompt "Your interests here" --max-articles 5 --output summary.mp3

serve:
	python -m vibe.main --serve

clean:
	rm -rf cache
