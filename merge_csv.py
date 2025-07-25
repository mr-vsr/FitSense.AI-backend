import pandas as pd
import os

# Path to your CSV files 
data_dir = "static/data"
csv_files = [
    "FOOD-DATA-GROUP1.csv",
    "FOOD-DATA-GROUP2.csv",
    "FOOD-DATA-GROUP3.csv",
    "FOOD-DATA-GROUP4.csv",
    "FOOD-DATA-GROUP5.csv",
]

df_list = []
for file in csv_files:
    file_path = os.path.join(data_dir, file)
    df = pd.read_csv(file_path)
    df_list.append(df)

merged_df = pd.concat(df_list, ignore_index=True)

merged_df.columns = [col.strip().lower().replace(" ", "_") for col in merged_df.columns]


if "food" in merged_df.columns:
    merged_df["food"] = merged_df["food"].astype(str).str.lower().str.strip()

merged_csv_path = os.path.join(data_dir, "merged_nutrition.csv")
merged_df.to_csv(merged_csv_path, index=False)

print(f"Merged CSV saved to {merged_csv_path}")
