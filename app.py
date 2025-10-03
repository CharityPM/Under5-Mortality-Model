import os
import pickle
import gdown
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import pandas as pd
from flask import Flask, jsonify, request
import dash_bootstrap_components as dbc

# ---------------------------
# Google Drive file IDs
# ---------------------------
MODEL_ID = "19H7NxVfaAK0Ml23X9jfTewVvZjcuJVhq"      # final_model.pkl
FEATURES_ID = "1LITbeocbOLTcZBmf0KeBTLcch_03oRi7"   # feature_importances.pkl

MODEL_PATH = "final_model.pkl"
FEATURES_PATH = "feature_importances.pkl"

def download_file(file_id, output):
    """Download file from Google Drive by ID"""
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    if not os.path.exists(output):
        print(f"⬇️ Downloading {output} ...")
        gdown.download(url, output, quiet=False)
    else:
        print(f"✅ {output} already exists")

def load_pickle(filename):
    """Safe pickle loader with debug info"""
    with open(filename, "rb") as f:
        return pickle.load(f)

# ---------------------------
# Download + Load Model and Features
# ---------------------------
try:
    download_file(MODEL_ID, MODEL_PATH)
    trained_models = load_pickle(MODEL_PATH)
    print("✅ Model loaded successfully")
except Exception as e:
    print(f"❌ Error loading model: {e}")
    trained_models = {}

try:
    download_file(FEATURES_ID, FEATURES_PATH)
    feature_importances = load_pickle(FEATURES_PATH)

    if not isinstance(feature_importances, pd.DataFrame):
        raise ValueError("feature_importances.pkl is not a DataFrame")

    print("✅ Features loaded successfully")
    print("Targets available:", feature_importances["Target"].unique().tolist())
except Exception as e:
    print(f"❌ Error loading features: {e}")
    feature_importances = pd.DataFrame(columns=["Target", "Feature", "Importance"])

# ---------------------------
# Extract top features dynamically
# ---------------------------
def get_top_features(target, top_n=20):
    if feature_importances.empty:
        return []
    filtered = feature_importances[
        feature_importances["Target"].str.lower() == target.lower()
    ]
    if filtered.empty:
        return []
    return filtered.nlargest(top_n, "Importance")["Feature"].tolist()

def make_dropdown(target):
    return dcc.Dropdown(
        id=f"dropdown-{target.lower()}",
        options=[{"label": f, "value": f} for f in get_top_features(target)],
        placeholder=f"Select features for {target}",
        multi=True
    )

# ---------------------------
# Flask server and routes
# ---------------------------
server = Flask(__name__)

@server.route("/")
def index():
    return """
    <div style="
        text-align:center;
        font-family:sans-serif;
        min-height: 100vh;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        color: #004080;
    ">
        <h1>👶 Afya Toto</h1>
        <p>Protecting Children’s Health Through Data Insights</p>
        <a href='/dashboard/'>Go to Dashboard</a>
    </div>
    """

@server.route("/api/features", methods=["GET"])
def api_features():
    if feature_importances.empty:
        return jsonify({"error": "❌ feature_importances is empty"})
    result = {}
    for t in feature_importances["Target"].unique():
        feats = (
            feature_importances[feature_importances["Target"] == t]
            .nlargest(20, "Importance")["Feature"]
            .tolist()
        )
        result[t] = feats
    return jsonify(result)

@server.route("/api/predict", methods=["POST"])
def api_predict():
    data = request.json
    prediction = trained_models.get("Under5", lambda x: "Model not loaded")(data)
    return jsonify({"prediction": prediction})

@server.route("/api/debug", methods=["GET"])
def api_debug():
    """Return debug info for models and features"""
    debug_info = {
        "model_loaded": bool(trained_models),
        "features_loaded": not feature_importances.empty,
        "feature_importances_shape": feature_importances.shape if not feature_importances.empty else (0, 0),
        "feature_importances_columns": feature_importances.columns.tolist(),
        "available_targets": feature_importances["Target"].unique().tolist() if not feature_importances.empty else [],
        "sample_rows": feature_importances.head(5).to_dict(orient="records") if not feature_importances.empty else []
    }
    return jsonify(debug_info)

# ---------------------------
# Dash app
# ---------------------------
app = dash.Dash(
    __name__,
    server=server,
    url_base_pathname="/dashboard/",
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)

app.layout = dbc.Container([
    dbc.Row([dbc.Col(html.H1("Afya-Toto Dashboard", className="text-center"), width=12)]),

    dbc.Row([
        dbc.Col(make_dropdown("Under5"), width=3),
        dbc.Col(make_dropdown("Infant"), width=3),
        dbc.Col(make_dropdown("Neonatal"), width=3),
    ], justify="center", className="mb-4"),

    dbc.Row([dbc.Col(html.Button("Predict", id="predict-btn", n_clicks=0, className="btn btn-success"), width="auto")],
            justify="center", className="mb-4"),

    dbc.Row([dbc.Col(html.Div(id="prediction-output", className="text-center"), width=12)])
], fluid=True)

@app.callback(
    Output("prediction-output", "children"),
    Input("predict-btn", "n_clicks"),
    State("dropdown-under5", "value"),
    State("dropdown-infant", "value"),
    State("dropdown-neonatal", "value")
)
def make_prediction(n_clicks, u5, inf, neo):
    if n_clicks < 1:
        return "ℹ️ Select features first."
    sel = {"Under5": u5 or [], "Infant": inf or [], "Neonatal": neo or []}
    return f"✅ Selected features: {sel}"

# ---------------------------
# Run server
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    server.run(debug=True, port=port)
