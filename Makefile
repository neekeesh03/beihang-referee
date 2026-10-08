.PHONY: test validate manifest serve benchmark demo release ccore-release

test:
	pytest -q

manifest:
	python scripts/rebuild_package_metadata.py

validate: manifest
	python scripts/validate_package.py

serve:
	referee serve

benchmark:
	referee benchmark evals/cases/major_comment_cases.json

demo:
	referee review examples/demo_manuscript.md --pipeline core --mode standard --provider scripted --scripted-responses examples/demo_responses.json --search-backend none --run-id demo

release:
	python scripts/build_release.py --output release-dist

ccore-release:
	rm -rf release-dist wheelhouse
