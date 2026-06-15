from pathlib import Path
from datetime import datetime, timezone
import json
import os

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


DATASET_PATH = Path(os.getenv("DIET_DATASET_PATH", "All_Diets.csv"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "outputs"))

REQUIRED_COLUMNS = {
    "Diet_type": ["Diet_type", "Diet type", "diet_type"],
    "Recipe_name": ["Recipe_name", "Recipe name", "recipe_name"],
    "Cuisine_type": ["Cuisine_type", "Cuisine type", "cuisine_type"],
    "Protein(g)": ["Protein(g)", "Protein (g)", "protein(g)", "protein"],
    "Carbs(g)": ["Carbs(g)", "Carbs (g)", "carbs(g)", "carbs"],
    "Fat(g)": ["Fat(g)", "Fat (g)", "fat(g)", "fat"],
}


def normalized_column_name(name: str) -> str:
    return str(name).strip().lower().replace(" ", "").replace("_", "")


def load_and_clean_data(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {csv_path}. Put All_Diets.csv in the project root "
            "or set DIET_DATASET_PATH."
        )

    df = pd.read_csv(csv_path)
    df.columns = [str(col).strip() for col in df.columns]

    normalized_actual_columns = {
        normalized_column_name(actual): actual for actual in df.columns
    }

    rename_map = {}
    missing = []
    for canonical, aliases in REQUIRED_COLUMNS.items():
        found = None
        for alias in aliases:
            found = normalized_actual_columns.get(normalized_column_name(alias))
            if found:
                break
        if found:
            rename_map[found] = canonical
        else:
            missing.append(canonical)

    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    df = df.rename(columns=rename_map)

    numeric_cols = ["Protein(g)", "Carbs(g)", "Fat(g)"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())
    df[numeric_cols] = df[numeric_cols].fillna(0)

    df["Diet_type"] = (
        df["Diet_type"].fillna("Unknown").astype(str).str.strip().str.title()
    )
    df["Cuisine_type"] = (
        df["Cuisine_type"]
        .fillna("unknown")
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", " ", regex=True)
    )
    df["Recipe_name"] = (
        df["Recipe_name"].fillna("Unknown Recipe").astype(str).str.strip()
    )

    df["Protein_to_Carbs_ratio"] = (
        df["Protein(g)"] / df["Carbs(g)"].where(df["Carbs(g)"] != 0)
    ).fillna(0)
    df["Carbs_to_Fat_ratio"] = (
        df["Carbs(g)"] / df["Fat(g)"].where(df["Fat(g)"] != 0)
    ).fillna(0)

    df["Protein_to_Carbs_ratio"] = df["Protein_to_Carbs_ratio"].round(4)
    df["Carbs_to_Fat_ratio"] = df["Carbs_to_Fat_ratio"].round(4)

    return df


def save_bar_chart(avg_macros: pd.DataFrame) -> None:
    plot_data = avg_macros.reset_index().melt(
        id_vars="Diet_type",
        value_vars=["Protein(g)", "Carbs(g)", "Fat(g)"],
        var_name="Macronutrient",
        value_name="Average grams",
    )

    plt.figure(figsize=(12, 7))
    sns.barplot(data=plot_data, x="Diet_type", y="Average grams", hue="Macronutrient")
    plt.title("Average Macronutrient Content by Diet Type")
    plt.xlabel("Diet Type")
    plt.ylabel("Average Grams")
    plt.xticks(rotation=35, ha="right")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "average_macros_bar.png", dpi=180)
    plt.close()


def save_heatmap(avg_macros: pd.DataFrame) -> None:
    plt.figure(figsize=(9, 6))
    sns.heatmap(avg_macros, annot=True, fmt=".1f", cmap="viridis", linewidths=0.5)
    plt.title("Macronutrient Heatmap by Diet Type")
    plt.xlabel("Macronutrient")
    plt.ylabel("Diet Type")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "macros_heatmap.png", dpi=180)
    plt.close()


def save_scatter_plot(top_protein: pd.DataFrame) -> None:
    plt.figure(figsize=(13, 7))
    sns.scatterplot(
        data=top_protein,
        x="Cuisine_type",
        y="Protein(g)",
        hue="Diet_type",
        size="Protein(g)",
        sizes=(60, 260),
        alpha=0.8,
    )
    plt.title("Top 5 Protein-Rich Recipes Per Diet Type by Cuisine")
    plt.xlabel("Cuisine Type")
    plt.ylabel("Protein (g)")
    plt.xticks(rotation=35, ha="right")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "top_protein_scatter.png", dpi=180)
    plt.close()


def analyze_dataset() -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_and_clean_data(DATASET_PATH)
    df.to_csv(OUTPUT_DIR / "cleaned_all_diets.csv", index=False)

    avg_macros = (
        df.groupby("Diet_type")[["Protein(g)", "Carbs(g)", "Fat(g)"]]
        .mean()
        .round(2)
    )
    avg_macros.to_csv(OUTPUT_DIR / "average_macros_by_diet.csv")

    top_protein = (
        df.sort_values("Protein(g)", ascending=False)
        .groupby("Diet_type", group_keys=False)
        .head(5)
    )
    top_protein.to_csv(OUTPUT_DIR / "top_5_protein_recipes_by_diet.csv", index=False)

    protein_totals = df.groupby("Diet_type")["Protein(g)"].sum().round(2)
    protein_averages = df.groupby("Diet_type")["Protein(g)"].mean().round(2)

    common_cuisines = (
        df.groupby(["Diet_type", "Cuisine_type"])
        .size()
        .reset_index(name="Recipe_count")
        .sort_values(["Diet_type", "Recipe_count"], ascending=[True, False])
    )
    common_cuisines.to_csv(OUTPUT_DIR / "cuisine_counts_by_diet.csv", index=False)

    most_common_cuisine_per_diet = (
        common_cuisines.groupby("Diet_type", group_keys=False).head(1)
    )
    most_common_cuisine_per_diet.to_csv(
        OUTPUT_DIR / "most_common_cuisine_per_diet.csv", index=False
    )

    save_bar_chart(avg_macros)
    save_heatmap(avg_macros)
    save_scatter_plot(top_protein)

    summary = {
        "processed_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_path": str(DATASET_PATH),
        "row_count": int(len(df)),
        "diet_type_count": int(df["Diet_type"].nunique()),
        "highest_total_protein_diet": {
            "Diet_type": protein_totals.idxmax(),
            "Total_protein_g": float(protein_totals.max()),
        },
        "highest_average_protein_diet": {
            "Diet_type": protein_averages.idxmax(),
            "Average_protein_g": float(protein_averages.max()),
        },
        "generated_files": [
            "cleaned_all_diets.csv",
            "average_macros_by_diet.csv",
            "top_5_protein_recipes_by_diet.csv",
            "cuisine_counts_by_diet.csv",
            "most_common_cuisine_per_diet.csv",
            "average_macros_bar.png",
            "macros_heatmap.png",
            "top_protein_scatter.png",
            "analysis_summary.json",
        ],
    }

    with open(OUTPUT_DIR / "analysis_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return summary


if __name__ == "__main__":
    result = analyze_dataset()
    print("Diet dataset analysis completed successfully.")
    print(json.dumps(result, indent=2))
