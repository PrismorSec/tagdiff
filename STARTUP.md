TagDiff Startup Commands

1) Install package:
python -m pip install .

2) Run CLI:
tagdiff owner/repo old_version new_version

3) Run module directly:
python -m tagdiff.cli owner/repo old_version new_version

4) Docker build + run:
docker build -t tagdiff-local .
docker run --rm tagdiff-local owner/repo old_version new_version
