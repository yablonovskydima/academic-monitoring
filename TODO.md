# TODO

Known issues in the data → features → model pipeline. Not fixed yet.

## Model versions don't record the target definition
`ml-service/src/ml_service/services/model_promotion_service.py`.

Promotion compares a new version's metric against the active one's, and training warm-starts from it. When the index formula or a label definition changes, the old models were trained on a different target, so the comparison and the warm start are meaningless - today the only way out is to drop the ML database and `trained_models/`. A target/feature schema version stored on `ModelVersion` would let promotion skip incompatible versions.
