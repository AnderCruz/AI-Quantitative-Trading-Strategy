Quantitative Trading II - Generic Walk-Forward Evaluator (initial isolated implementation)

Files:
  src/walk_forward_evaluation.py
  tests/test_walk_forward_evaluation.py

Copy both files into the matching directories in ~/projects/Quantitative-Trading.
These files add a generic evaluator and synthetic-data unit tests only. They do not
modify the existing Ridge, Random Forest, LightGBM evaluators or runner scripts.
No financial data is loaded and no financial experiment is run by these tests.

From the project root, run:
  pytest -q tests/test_walk_forward_evaluation.py

Only after reviewing the results should existing evaluators be migrated to delegate
to this generic module. Do not run the existing real-data evaluation scripts as part
of this implementation step.
