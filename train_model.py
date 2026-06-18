import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

# =====================================
# LOAD DATASET
# =====================================

df = pd.read_csv("jobs.csv")

print("\nDataset Loaded\n")

print(df.head())

# =====================================
# FEATURES
# =====================================

X = df[[
    "role",
    "city",
    "experience_required",
    "skills",
    "degree",
    "company_type",
    "internship_experience"
]]

# =====================================
# TARGET
# =====================================

y = df["salary_lpa"]

# =====================================
# CATEGORICAL FEATURES
# =====================================

categorical_features = [
    "role",
    "city",
    "skills",
    "degree",
    "company_type",
    "internship_experience"
]

# =====================================
# PREPROCESSOR
# =====================================

preprocessor = ColumnTransformer(
    transformers=[
        (
            "cat",
            OneHotEncoder(handle_unknown="ignore"),
            categorical_features
        )
    ],
    remainder="passthrough"
)

# =====================================
# MODEL
# =====================================

model = Pipeline([
    (
        "preprocessor",
        preprocessor
    ),
    (
        "regressor",
        RandomForestRegressor(
            n_estimators=500,
            max_depth=20,
            random_state=42
        )
    )
])

# =====================================
# SPLIT DATA
# =====================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)

# =====================================
# TRAIN MODEL
# =====================================

print("\nTraining Model...\n")

model.fit(X_train, y_train)

# =====================================
# TEST MODEL
# =====================================

predictions = model.predict(X_test)

# =====================================
# ERROR
# =====================================

error = mean_absolute_error(
    y_test,
    predictions
)

print("✅ Model Trained Successfully")

print()

print("📉 Mean Absolute Error:", round(error, 2))

# =====================================
# SAVE MODEL
# =====================================

joblib.dump(model, "salary_model.pkl")

print()

print("💾 salary_model.pkl saved successfully")