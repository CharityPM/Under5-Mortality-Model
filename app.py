import os
import pickle
import gdown
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
from flask import Flask

# ---------------------------
# Google Drive file IDs
# ---------------------------
FEATURES_FILE_ID = "1Wp4NOmMveYMql2h8GVfyx0J8pmNU7pkQ"  # feature_importances.pkl
MODEL_FILE_ID = "1sxZBckDWmumOd7Yilg4_0oudNlqLOWZu"     # final_model.pkl

FEATURES_PATH = "feature_importances.pkl"
MODEL_PATH = "final_model.pkl"

# ---------------------------
# Download files if not present
# ---------------------------
for file_id, path in [(FEATURES_FILE_ID, FEATURES_PATH), (MODEL_FILE_ID, MODEL_PATH)]:
    if not os.path.exists(path):
        url = f"https://drive.google.com/uc?id={file_id}"
        print(f"Downloading {path} from Google Drive...")
        gdown.download(url, path, quiet=False)

# ---------------------------
# Load features & model
# ---------------------------
try:
    with open(FEATURES_PATH, "rb") as f:
        feature_importances = pickle.load(f)
    print("✅ Feature importances loaded.")
except Exception as e:
    print("❌ Error loading feature importances:", e)
    feature_importances = []

# Kenya-focused top features
kenya_features = [
    'num__child_death_history', 'cat__Region_Kwale', 'num__Weight/Age standard deviation (new WHO)',
    'num__Childs height in centimeters (1 decimal)', 'cat__Region_Isiolo', 'cat__Region_Laikipia',
    'cat__Region_Mombasa', 'cat__Region_Nairobi', 'cat__Region_Baringo',
    'num__Childs weight in kilograms (1 decimal)'
]

try:
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    print("✅ Model loaded.")
except Exception as e:
    print("❌ Error loading model:", e)
    model = None

# ---------------------------
# Flask server
# ---------------------------
server = Flask(__name__)

@server.route("/")
def index():
    return """
    <div style="
        text-align:center; 
        font-family:sans-serif; 
        height: 100vh;
        background-image: url('https://i.pinimg.com/1200x/97/a9/1c/97a91c944845237ef509452fec78863f.jpg');
        background-size: cover;
        background-position: center;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        color: white;
        text-shadow: 1px 1px 5px rgba(0,0,0,0.7);
    ">
        <h1 style='font-size: 4em;'>👶 Afya-Toto</h1>
        <p style='font-size: 1.5em;'>Under-5 Mortality Risk Prediction Tool - Kenya</p>
        <a href='/dashboard/' style='
            display:inline-block;
            margin-top:25px;
            padding:15px 30px;
            background:#007BFF;
            color:white;
            border-radius:10px;
            text-decoration:none;
            font-weight:bold;
            font-size: 18px;
        '>Go to Dashboard</a>
    </div>
    """

# ---------------------------
# Dash app
# ---------------------------
app = dash.Dash(
    __name__,
    server=server,
    url_base_pathname="/dashboard/",
    suppress_callback_exceptions=True
)

# Layout
app.layout = html.Div(
    style={"display": "flex", "minHeight": "100vh", "fontFamily": "sans-serif"},
    children=[
        # Sidebar
        html.Div(
            style={
                "flex": "1",
                "backgroundColor": "#e0f7fa",
                "padding": "30px",
                "borderRight": "2px solid #b2ebf2",
                "display": "flex",
                "flexDirection": "column",
                "justifyContent": "flex-start"
            },
            children=[
                html.H2("👶 Afya-Toto Inputs", style={"textAlign": "center", "color": "#007BFF", "marginBottom": "30px"}),

                html.Div(style={"marginBottom": "20px"}, children=[
                    html.P("Select feature(s):", style={"fontWeight": "bold"}),
                    dcc.Dropdown(
                        id="feature-dropdown",
                        options=[{"label": f, "value": f} for f in kenya_features],
                        placeholder="Select feature(s)",
                        multi=True,
                        searchable=True,
                    ),
                ]),

                html.Div(style={"marginBottom": "20px"}, children=[
                    html.P("Select target variable:", style={"fontWeight": "bold"}),
                    dcc.Dropdown(
                        id="target-dropdown",
                        options=[
                            {"label": "Under-5", "value": "Under5"},
                            {"label": "Infant", "value": "Infant"},
                            {"label": "Neonatal", "value": "Neonatal"}
                        ],
                        placeholder="Select target variable",
                    ),
                ]),

                html.Button(
                    "👶 Predict",
                    id="predict-button",
                    n_clicks=0,
                    style={
                        "width": "100%",
                        "padding": "12px",
                        "backgroundColor": "#007BFF",
                        "color": "white",
                        "border": "none",
                        "borderRadius": "8px",
                        "fontSize": "16px",
                        "cursor": "pointer",
                        "marginTop": "10px"
                    },
                ),
            ],
        ),

        # Main panel
        html.Div(
            style={"flex": "3", "padding": "30px", "backgroundColor": "#f5f5f5"},
            children=[
                html.H2("📊 Prediction Results", style={"color": "#333", "marginBottom": "20px"}),
                dcc.Loading(
                    id="loading-spinner",
                    type="circle",
                    children=dcc.Graph(id="prediction-chart"),
                ),
            ],
        ),
    ],
)

# ---------------------------
# Dash Callback
# ---------------------------
@app.callback(
    Output("prediction-chart", "figure"),
    [Input("predict-button", "n_clicks")],
    [State("feature-dropdown", "value"), State("target-dropdown", "value")],
)
def update_chart(n_clicks, features_selected, target_value):
    if n_clicks == 0 or not features_selected or not target_value:
        return go.Figure().update_layout(
            title_text="Select features + target, then click Predict",
            xaxis={"visible": False},
            yaxis={"visible": False},
            annotations=[{
                "text": "Waiting for input...",
                "xref": "paper", "yref": "paper",
                "showarrow": False,
                "font": {"size": 16, "color": "#888"}
            }],
        )

    try:
        pred = model.predict([features_selected]).tolist()[0]
    except Exception as e:
        return go.Figure().update_layout(
            title_text="Error",
            annotations=[{
                "text": str(e),
                "xref": "paper", "yref": "paper",
                "showarrow": False,
                "font": {"size": 14, "color": "red"}
            }],
        )

    color = "red" if pred > 0.5 else "green"
    icon = "⚠️" if pred > 0.5 else "✅"

    fig = go.Figure(data=[go.Bar(
        x=[f"{icon} {target_value}"],
        y=[pred],
        marker_color=color,
        text=[f"{pred:.2f}"],
        textposition="auto"
    )])

    fig.update_layout(
        title_text=f"Prediction for {target_value}",
        yaxis_title="Predicted Risk",
        plot_bgcolor="white",
        paper_bgcolor="#f5f5f5",
        font={"color": "#333"},
    )
    return fig

# ---------------------------
# Run server
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    server.run(debug=False, port=port, host="0.0.0.0")
