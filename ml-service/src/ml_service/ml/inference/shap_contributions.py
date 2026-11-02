import random

import pandas as pd
import shap

TOP_N_CONTRIBUTIONS = 5
BACKGROUND_SIZE = 100
BACKGROUND_SEED = 0


def background_sample(rows: list, size: int = BACKGROUND_SIZE) -> list:
    return random.Random(BACKGROUND_SEED).sample(rows, min(size, len(rows)))


def make_explainer(model, background: pd.DataFrame) -> shap.TreeExplainer:
    return shap.TreeExplainer(
        model.get_booster(),
        data=background,
        feature_perturbation="interventional",
    )


def top_contributions(feature_row: pd.Series, shap_row, top_n: int = TOP_N_CONTRIBUTIONS) -> list[dict]:
    contributions = list(zip(feature_row.index.tolist(), feature_row.values.tolist(), shap_row))
    contributions.sort(key=lambda item: abs(item[2]), reverse=True)

    return [
        {
            "feature_name": name,
            "feature_value": float(value),
            "shap_value": float(shap_value),
            "rank": rank + 1,
        }
        for rank, (name, value, shap_value) in enumerate(contributions[:top_n])
    ]
