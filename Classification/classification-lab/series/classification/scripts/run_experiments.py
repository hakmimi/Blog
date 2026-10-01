"""Run every experiment and generate all publication artifacts.

The final holdout is evaluated only after hyperparameters are selected from
chronological folds in the development prefix. Run from the repository root:
    python scripts/run_experiments.py
"""
from __future__ import annotations

import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")

import json
import math
import time
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.calibration import calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.datasets import make_classification, make_moons
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis, QuadraticDiscriminantAnalysis
from sklearn.ensemble import ExtraTreesClassifier, GradientBoostingClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, balanced_accuracy_score,
    brier_score_loss, confusion_matrix, f1_score, log_loss, precision_recall_curve,
    precision_score, recall_score, roc_auc_score, roc_curve)
from sklearn.model_selection import ParameterGrid, ParameterSampler
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler
from sklearn.svm import LinearSVC, SVC
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw" / "bank-additional-full.csv"
ART = ROOT / "artifacts"
FIG = ROOT / "figures"
SEED = 20260930
COLORS = {"navy": "#17324d", "blue": "#2a6fbb", "teal": "#168c84", "gold": "#e1a72f", "coral": "#d95f59", "gray": "#75808a"}


def style() -> None:
    plt.rcParams.update({
        "figure.dpi": 140, "savefig.dpi": 180, "font.size": 10,
        "axes.titlesize": 12, "axes.labelsize": 10, "axes.spines.top": False,
        "axes.spines.right": False, "axes.grid": True, "grid.alpha": .18,
        "figure.facecolor": "white", "axes.facecolor": "#fbfcfd",
    })


def savefig(name: str) -> None:
    plt.tight_layout()
    plt.savefig(FIG / name, bbox_inches="tight")
    plt.close()


def chronological_folds(n: int) -> list[tuple[np.ndarray, np.ndarray]]:
    edges = [int(n * x) for x in (.50, .665, .83, 1.0)]
    folds = []
    for train_end, valid_end in zip(edges[:-1], edges[1:]):
        folds.append((np.arange(train_end), np.arange(train_end, valid_end)))
    return folds


def metrics(y: np.ndarray, p: np.ndarray, threshold: float = .5) -> dict[str, float]:
    pred = p >= threshold
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "accuracy": accuracy_score(y, pred),
        "balanced_accuracy": balanced_accuracy_score(y, pred),
        "precision": precision_score(y, pred, zero_division=0),
        "recall": recall_score(y, pred, zero_division=0),
        "specificity": tn / (tn + fp),
        "f1": f1_score(y, pred, zero_division=0),
        "roc_auc": roc_auc_score(y, p),
        "average_precision": average_precision_score(y, p),
        "log_loss": log_loss(y, p),
        "brier": brier_score_loss(y, p),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    }


def preprocessors(X: pd.DataFrame) -> tuple[list[str], list[str], ColumnTransformer, ColumnTransformer]:
    cat = X.select_dtypes(include="object").columns.tolist()
    num = [c for c in X.columns if c not in cat]
    sparse = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat),
        ("num", Pipeline([("impute", SimpleImputer()), ("scale", StandardScaler())]), num),
    ])
    dense = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False, drop="if_binary"), cat),
        ("num", Pipeline([("impute", SimpleImputer()), ("scale", StandardScaler())]), num),
    ])
    return cat, num, sparse, dense


def tune(name: str, pipeline: Pipeline, grid: dict, X: pd.DataFrame, y: np.ndarray, folds) -> tuple[Pipeline, dict, pd.DataFrame]:
    rows = []
    for params in ParameterGrid(grid):
        fold_scores = []
        for train_idx, valid_idx in folds:
            if len(np.unique(y[train_idx])) < 2 or len(np.unique(y[valid_idx])) < 2:
                raise ValueError(f"class absent in chronological fold for {name}")
            candidate = clone(pipeline).set_params(**params)
            candidate.fit(X.iloc[train_idx], y[train_idx])
            p = candidate.predict_proba(X.iloc[valid_idx])[:, 1]
            fold_scores.append(average_precision_score(y[valid_idx], p))
        rows.append({"model": name, "params": json.dumps(params, sort_keys=True),
                     "mean_cv_ap": float(np.mean(fold_scores)), "fold_ap": json.dumps(fold_scores)})
    table = pd.DataFrame(rows).sort_values("mean_cv_ap", ascending=False)
    best_params = json.loads(table.iloc[0]["params"])
    fitted = clone(pipeline).set_params(**best_params).fit(X, y)
    return fitted, best_params, table


def primary_benchmark(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, np.ndarray], dict]:
    split = int(len(df) * .8)
    dev, hold = df.iloc[:split].copy(), df.iloc[split:].copy()
    features = [c for c in df.columns if c not in ("y", "duration")]
    Xd, Xh = dev[features], hold[features]
    yd = (dev.y == "yes").astype(int).to_numpy()
    yh = (hold.y == "yes").astype(int).to_numpy()
    folds = chronological_folds(len(dev))
    _, _, sparse, dense = preprocessors(Xd)
    specs = {
        "Logistic regression": (Pipeline([("prep", sparse), ("model", LogisticRegression(max_iter=1000, solver="liblinear", random_state=SEED))]), {"model__C": [.1, 1.0]}),
        "Gaussian Naive Bayes": (Pipeline([("prep", dense), ("model", GaussianNB())]), {"model__var_smoothing": [1e-8, 1e-7]}),
        "Decision tree": (Pipeline([("prep", sparse), ("model", DecisionTreeClassifier(random_state=SEED))]), {"model__min_samples_leaf": [20, 100]}),
        "Random forest": (Pipeline([("prep", sparse), ("model", RandomForestClassifier(n_estimators=180, n_jobs=1, random_state=SEED, max_features="sqrt"))]), {"model__min_samples_leaf": [5, 20]}),
        "Extra Trees": (Pipeline([("prep", sparse), ("model", ExtraTreesClassifier(n_estimators=180, n_jobs=1, random_state=SEED, max_features="sqrt"))]), {"model__min_samples_leaf": [5, 20]}),
        "Histogram gradient boosting": (Pipeline([("prep", dense), ("model", HistGradientBoostingClassifier(max_iter=140, max_leaf_nodes=15, random_state=SEED))]), {"model__learning_rate": [.05, .1]}),
    }
    results, predictions, cv_tables, selected = [], {}, [], {}
    majority_p = np.full(len(yh), yd.mean())
    majority_m = metrics(yh, majority_p, threshold=1.0)
    results.append({"model": "Majority class", "selected_params": "{}", **majority_m})
    predictions["Majority class"] = majority_p
    for name, (pipe, grid) in specs.items():
        print(f"tuning {name}", flush=True)
        fitted, params, cv = tune(name, pipe, grid, Xd, yd, folds)
        p = fitted.predict_proba(Xh)[:, 1]
        results.append({"model": name, "selected_params": json.dumps(params), **metrics(yh, p)})
        predictions[name] = p
        cv_tables.append(cv)
        selected[name] = fitted
    result = pd.DataFrame(results)
    result.to_csv(ART / "primary_benchmark.csv", index=False)
    pd.concat(cv_tables, ignore_index=True).to_csv(ART / "chronological_cv_results.csv", index=False)
    pred_frame = pd.DataFrame({"row_index": hold.index, "y": yh, **predictions})
    pred_frame.to_csv(ART / "holdout_predictions.csv", index=False)
    split_info = {
        "total_rows": len(df), "development_rows": len(dev), "holdout_rows": len(hold),
        "split_row": split, "development_prevalence": float(yd.mean()),
        "holdout_prevalence": float(yh.mean()), "feature_count_primary": len(features),
        "excluded_primary": ["duration"],
        "folds": [{"train_start": int(t[0]), "train_end_exclusive": int(t[-1] + 1),
                   "validation_start": int(v[0]), "validation_end_exclusive": int(v[-1] + 1),
                   "train_positive": int(yd[t].sum()), "validation_positive": int(yd[v].sum())} for t, v in folds],
    }
    (ART / "split_manifest.json").write_text(json.dumps(split_info, indent=2) + "\n")
    return result, predictions, {"dev": dev, "hold": hold, "Xd": Xd, "Xh": Xh, "yd": yd, "yh": yh, "folds": folds, "models": selected}


def plot_primary(result: pd.DataFrame, predictions: dict[str, np.ndarray], ctx: dict) -> None:
    yh = ctx["yh"]
    plot = result[result.model != "Majority class"].sort_values("average_precision")
    fig, ax = plt.subplots(figsize=(8, 4.8))
    y = np.arange(len(plot))
    ax.barh(y - .17, plot.average_precision, .34, label="Average precision", color=COLORS["teal"])
    ax.barh(y + .17, plot.roc_auc, .34, label="ROC-AUC", color=COLORS["blue"])
    ax.axvline(yh.mean(), color=COLORS["coral"], ls="--", lw=1, label=f"Holdout prevalence ({yh.mean():.1%})")
    ax.set_yticks(y, plot.model); ax.set_xlim(0, 1); ax.set_xlabel("Score on locked chronological holdout")
    ax.set_title("Ranking quality depends on both model and metric"); ax.legend(loc="lower right")
    savefig("primary-benchmark.png")

    best = result[result.model != "Majority class"].sort_values("average_precision", ascending=False).iloc[0].model
    p = predictions[best]
    fpr, tpr, _ = roc_curve(yh, p)
    precision, recall, _ = precision_recall_curve(yh, p)
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    axes[0].plot(fpr, tpr, color=COLORS["blue"], label=f"{best} ({roc_auc_score(yh,p):.3f})")
    axes[0].plot([0,1],[0,1], ls="--", color=COLORS["gray"]); axes[0].set(xlabel="False-positive rate", ylabel="True-positive rate", title="ROC curve"); axes[0].legend()
    axes[1].plot(recall, precision, color=COLORS["teal"], label=f"{best} ({average_precision_score(yh,p):.3f})")
    axes[1].axhline(yh.mean(), ls="--", color=COLORS["gray"], label="Prevalence")
    axes[1].set(xlabel="Recall", ylabel="Precision", title="Precision–recall curve"); axes[1].legend()
    savefig("roc-pr-curves.png")

    m = metrics(yh, p)
    cm = np.array([[m["tn"], m["fp"]], [m["fn"], m["tp"]]])
    fig, ax = plt.subplots(figsize=(5, 4)); im = ax.imshow(cm, cmap="Blues")
    for (i,j), val in np.ndenumerate(cm): ax.text(j, i, f"{val:,}", ha="center", va="center", fontsize=13, color="white" if val > cm.max()/2 else COLORS["navy"])
    ax.set(xticks=[0,1], yticks=[0,1], xticklabels=["Predict no","Predict yes"], yticklabels=["Actual no","Actual yes"], title=f"{best} at threshold 0.50", xlabel="Prediction", ylabel="Outcome")
    savefig("confusion-matrix.png")


def leakage_experiment(df: pd.DataFrame, ctx: dict) -> pd.DataFrame:
    split = int(len(df) * .8); dev, hold = df.iloc[:split], df.iloc[split:]
    rows = []
    for label, exclude_duration in [("Start-of-call features", True), ("Adds current-call duration (unavailable)", False)]:
        feats = [c for c in df.columns if c != "y" and (not exclude_duration or c != "duration")]
        _, _, sparse, _ = preprocessors(dev[feats])
        model = Pipeline([("prep", sparse), ("model", LogisticRegression(C=.1, max_iter=1000, solver="liblinear", random_state=SEED))])
        model.fit(dev[feats], (dev.y == "yes").astype(int))
        p = model.predict_proba(hold[feats])[:,1]
        rows.append({"scenario": label, **metrics((hold.y == "yes").astype(int).to_numpy(), p)})
    out = pd.DataFrame(rows); out.to_csv(ART / "prediction_moment_comparison.csv", index=False)
    fig, ax = plt.subplots(figsize=(7.5, 3.7)); x=np.arange(2); w=.34
    ax.bar(x-w/2, out.roc_auc, w, label="ROC-AUC", color=COLORS["blue"]); ax.bar(x+w/2, out.average_precision, w, label="Average precision", color=COLORS["teal"])
    ax.set_xticks(x, ["Known at start\nof call", "Illegitimately adds\ncall duration"]); ax.set_ylim(0,1); ax.set_ylabel("Locked-holdout score"); ax.set_title("A prediction-moment violation creates an optimistic comparison"); ax.legend()
    savefig("duration-prediction-moment.png")
    return out


def synthetic_mechanisms() -> pd.DataFrame:
    rng = np.random.default_rng(SEED); rows=[]
    settings = [
        ("Baseline", dict(weights=[.7,.3], class_sep=1.2, flip_y=.01)),
        ("Rare positive", dict(weights=[.95,.05], class_sep=1.2, flip_y=.01)),
        ("More overlap", dict(weights=[.7,.3], class_sep=.55, flip_y=.01)),
        ("Label noise", dict(weights=[.7,.3], class_sep=1.2, flip_y=.18)),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(11, 7))
    for ax, (name, kw) in zip(axes.flat, settings):
        X,y=make_classification(n_samples=900,n_features=2,n_redundant=0,n_informative=2,n_clusters_per_class=1,random_state=SEED,**kw)
        model=LogisticRegression().fit(X,y); p=model.predict_proba(X)[:,1]
        rows.append({"factor":name,"prevalence":y.mean(),"roc_auc":roc_auc_score(y,p),"average_precision":average_precision_score(y,p)})
        ax.scatter(X[:,0],X[:,1],c=np.where(y, COLORS["coral"], COLORS["blue"]),s=8,alpha=.55); ax.set_title(name)
    X,y=make_classification(n_samples=900,n_features=2,n_informative=1,n_redundant=1,n_clusters_per_class=1,class_sep=1.1,flip_y=.01,random_state=SEED)
    p=LogisticRegression().fit(X,y).predict_proba(X)[:,1]; rows.append({"factor":"Correlated features","prevalence":y.mean(),"roc_auc":roc_auc_score(y,p),"average_precision":average_precision_score(y,p)})
    axes.flat[4].scatter(X[:,0],X[:,1],c=np.where(y,COLORS["coral"],COLORS["blue"]),s=8,alpha=.55); axes.flat[4].set_title("Correlated features")
    X,y=make_moons(n_samples=900,noise=.22,random_state=SEED); p=LogisticRegression().fit(X,y).predict_proba(X)[:,1]; rows.append({"factor":"Nonlinear boundary","prevalence":y.mean(),"roc_auc":roc_auc_score(y,p),"average_precision":average_precision_score(y,p)})
    axes.flat[5].scatter(X[:,0],X[:,1],c=np.where(y,COLORS["coral"],COLORS["blue"]),s=8,alpha=.55); axes.flat[5].set_title("Nonlinear boundary")
    for ax in axes.flat: ax.set(xticks=[],yticks=[])
    fig.suptitle("Controlled datasets isolate one difficulty at a time", fontsize=14)
    savefig("synthetic-difficulties.png")

    # A distribution-shift track: same conditional rule, translated test population.
    Xall,yall=make_classification(n_samples=3500,n_features=2,n_redundant=0,n_informative=2,class_sep=1.1,weights=[.8,.2],random_state=SEED)
    Xtr,ytr=Xall[:2000],yall[:2000]
    model=LogisticRegression().fit(Xtr,ytr)
    shift_rows=[]
    for shift in [0, .5, 1.0, 1.5]:
        Xte,yte=Xall[2000:].copy(),yall[2000:]
        Xte[:,0]+=shift; p=model.predict_proba(Xte)[:,1]
        shift_rows.append({"shift":shift,"roc_auc":roc_auc_score(yte,p),"average_precision":average_precision_score(yte,p),"brier":brier_score_loss(yte,p)})
    shift_df=pd.DataFrame(shift_rows); shift_df.to_csv(ART/"synthetic_shift.csv",index=False)
    fig,ax=plt.subplots(figsize=(7,4)); ax.plot(shift_df["shift"],shift_df.roc_auc,"o-",label="ROC-AUC"); ax.plot(shift_df["shift"],shift_df.average_precision,"o-",label="Average precision"); ax.plot(shift_df["shift"],shift_df.brier,"o-",label="Brier (lower is better)"); ax.set(xlabel="Translation applied to test feature 1",ylabel="Metric",title="Distribution shift changes performance without retraining"); ax.legend(); savefig("synthetic-shift.png")
    out=pd.DataFrame(rows); out.to_csv(ART/"synthetic_mechanisms.csv",index=False); return out


def objective_experiment() -> pd.DataFrame:
    X,y=make_classification(n_samples=1800,n_features=2,n_redundant=0,n_informative=2,n_clusters_per_class=1,weights=[.88,.12],class_sep=.85,flip_y=.04,random_state=SEED)
    X=StandardScaler().fit_transform(X); rng=np.random.default_rng(SEED); idx=rng.permutation(len(y)); tr,te=idx[:1200],idx[1200:]
    def sigmoid(z): return 1/(1+np.exp(-np.clip(z,-30,30)))
    def fit(loss):
        w=np.zeros(3); Xa=np.c_[np.ones(len(tr)),X[tr]]; lr=.04
        for step in range(2500):
            z=Xa@w; p=sigmoid(z); yy=y[tr]
            if loss=="Log loss": grad=Xa.T@(p-yy)/len(yy)
            elif loss=="Class-weighted log loss":
                weights=np.where(yy==1,(yy==0).sum()/max((yy==1).sum(),1),1.0); grad=Xa.T@((p-yy)*weights)/weights.sum()
            elif loss=="Brier loss": grad=Xa.T@(2*(p-yy)*p*(1-p))/len(yy)
            else:
                ys=2*yy-1; margin=ys*z; active=margin<1; grad=-(Xa[active].T@ys[active])/len(yy) if active.any() else np.zeros_like(w)
            w-=lr*grad
        return w
    losses=["Log loss","Class-weighted log loss","Brier loss","Hinge loss"]; rows=[]
    fig,axes=plt.subplots(1,4,figsize=(12,3.2),sharex=True,sharey=True)
    xx,yy=np.meshgrid(np.linspace(X[:,0].min(),X[:,0].max(),180),np.linspace(X[:,1].min(),X[:,1].max(),180)); grid=np.c_[np.ones(xx.size),xx.ravel(),yy.ravel()]
    for ax,name in zip(axes,losses):
        w=fit(name); raw=np.c_[np.ones(len(te)),X[te]]@w; p=sigmoid(raw)
        rows.append({"objective":name,**metrics(y[te],p)})
        zz=(grid@w).reshape(xx.shape); ax.contourf(xx,yy,zz,levels=[-99,0,99],colors=["#dbe8f5","#f7d9d6"],alpha=.8); ax.contour(xx,yy,zz,levels=[0],colors=COLORS["navy"],linewidths=1.5); ax.scatter(X[te,0],X[te,1],c=np.where(y[te],COLORS["coral"],COLORS["blue"]),s=7,alpha=.6); ax.set_title(name,fontsize=9); ax.set(xticks=[],yticks=[])
    fig.suptitle("Same linear score family, same data, different training objectives",fontsize=13); savefig("objective-boundaries.png")
    out=pd.DataFrame(rows); out.to_csv(ART/"objective_comparison.csv",index=False)

    ps=np.linspace(.001,.999,500); fig,axes=plt.subplots(1,2,figsize=(9,3.7))
    axes[0].plot(ps,-np.log(ps),label="Positive example",color=COLORS["coral"]); axes[0].plot(ps,-np.log(1-ps),label="Negative example",color=COLORS["blue"]); axes[0].plot(ps,(1-ps)**2,ls="--",label="Brier, positive",color=COLORS["gold"]); axes[0].set(xlabel="Predicted probability p",ylabel="Loss",ylim=(0,6),title="Probability losses penalize confidence differently"); axes[0].legend(fontsize=8)
    q=np.linspace(0,1,300); gini=2*q*(1-q); entropy=-(q*np.log2(np.clip(q,1e-9,1))+ (1-q)*np.log2(np.clip(1-q,1e-9,1))); axes[1].plot(q,gini,label="Gini",color=COLORS["teal"]); axes[1].plot(q,entropy,label="Entropy",color=COLORS["blue"]); axes[1].set(xlabel="Positive proportion in node",ylabel="Impurity",title="Both criteria prefer pure nodes"); axes[1].legend(); savefig("loss-and-impurity.png")
    return out


def tree_split_visual() -> pd.DataFrame:
    x=np.array([.08,.14,.20,.29,.35,.43,.51,.58,.66,.72,.79,.88]); y=np.array([0,0,1,0,0,1,0,1,1,0,1,1]); thresholds=(x[:-1]+x[1:])/2
    def impurity(a,kind):
        if len(a)==0:return 0
        p=a.mean()
        return 2*p*(1-p) if kind=="gini" else -(p*math.log2(p) if p else 0)-((1-p)*math.log2(1-p) if p<1 else 0)
    rows=[]
    for t in thresholds:
        left=y[x<=t]; right=y[x>t]
        rows.append({"threshold":t,"left_n":len(left),"left_positive":int(left.sum()),"right_n":len(right),"right_positive":int(right.sum()),"weighted_gini":len(left)/len(y)*impurity(left,"gini")+len(right)/len(y)*impurity(right,"gini"),"weighted_entropy":len(left)/len(y)*impurity(left,"entropy")+len(right)/len(y)*impurity(right,"entropy")})
    out=pd.DataFrame(rows); out.to_csv(ART/"candidate_splits.csv",index=False); best=out.loc[out.weighted_gini.idxmin()]
    fig,axes=plt.subplots(2,2,figsize=(9,6)); candidates=[thresholds[1],thresholds[4],float(best.threshold),thresholds[-2]]
    for i,(ax,t) in enumerate(zip(axes.flat,candidates),1):
        ax.scatter(x,np.zeros_like(x),c=np.where(y,COLORS["coral"],COLORS["blue"]),s=70,edgecolor="white"); ax.axvline(t,color=COLORS["navy"],ls="--"); row=out.iloc[np.argmin(abs(out.threshold-t))]; ax.set(yticks=[],xlabel="Feature value",title=f"Step {i}: split {t:.2f} · weighted Gini {row.weighted_gini:.3f}"); ax.text(.02,.80,f"left: {row.left_positive}/{row.left_n} positive",transform=ax.transAxes); ax.text(.60,.80,f"right: {row.right_positive}/{row.right_n} positive",transform=ax.transAxes)
    fig.suptitle("Candidate splits change the class mixture in both children",fontsize=13); savefig("tree-split-steps.png"); return out


def boosting_visual() -> pd.DataFrame:
    X,y=make_moons(n_samples=2200,noise=.28,random_state=SEED); Xtr,Xte=X[:1500],X[1500:]; ytr,yte=y[:1500],y[1500:]
    model=GradientBoostingClassifier(n_estimators=120,learning_rate=.05,max_depth=2,random_state=SEED).fit(Xtr,ytr)
    rows=[]
    for i,p in enumerate(model.staged_predict_proba(Xte),1):
        if i in {1,5,10,20,40,80,120}: rows.append({"trees":i,"average_precision":average_precision_score(yte,p[:,1]),"log_loss":log_loss(yte,p[:,1])})
    out=pd.DataFrame(rows); out.to_csv(ART/"boosting_stages.csv",index=False)
    fig,ax1=plt.subplots(figsize=(7,4)); ax1.plot(out.trees,out.average_precision,"o-",color=COLORS["teal"],label="Average precision"); ax1.set(xlabel="Boosting stages",ylabel="Average precision",title="Small sequential corrections build a nonlinear classifier"); ax2=ax1.twinx(); ax2.plot(out.trees,out.log_loss,"s--",color=COLORS["coral"],label="Log loss"); ax2.set_ylabel("Log loss"); lines=ax1.lines+ax2.lines; ax1.legend(lines,[l.get_label() for l in lines],loc="center right"); savefig("boosting-stages.png"); return out


def other_families(ctx: dict) -> pd.DataFrame:
    # Declared bounded chronological subset: first 6,000 train, next 2,000 validation.
    X=ctx["Xd"].iloc[:8000]; y=ctx["yd"][:8000]; Xtr,Xv=X.iloc[:6000],X.iloc[6000:]; ytr,yv=y[:6000],y[6000:]
    _,_,_,dense=preprocessors(X)
    specs={
        "k-nearest neighbors": KNeighborsClassifier(n_neighbors=35,weights="distance"),
        "Linear SVM": LinearSVC(C=.1,dual="auto",random_state=SEED),
        "RBF SVM": SVC(C=1,probability=True,random_state=SEED),
        "LDA": LinearDiscriminantAnalysis(solver="lsqr",shrinkage="auto"),
        "QDA": QuadraticDiscriminantAnalysis(reg_param=.3),
        "Small MLP": MLPClassifier(hidden_layer_sizes=(24,),max_iter=250,early_stopping=True,random_state=SEED),
    }; rows=[]
    for name,est in specs.items():
        print(f"fitting subset model {name}",flush=True); pipe=Pipeline([("prep",clone(dense)),("model",est)]); start=time.perf_counter()
        with warnings.catch_warnings(): warnings.simplefilter("ignore"); pipe.fit(Xtr,ytr)
        elapsed=time.perf_counter()-start
        if hasattr(pipe,"predict_proba"): p=pipe.predict_proba(Xv)[:,1]
        else: 
            s=pipe.decision_function(Xv); p=1/(1+np.exp(-np.clip(s,-30,30)))
        rows.append({"model":name,"train_rows":6000,"validation_rows":2000,"fit_seconds":elapsed,**metrics(yv,p)})
    out=pd.DataFrame(rows); out.to_csv(ART/"other_families_subset.csv",index=False)
    fig,ax=plt.subplots(figsize=(8,4.5)); order=out.sort_values("average_precision"); ax.barh(order.model,order.average_precision,color=COLORS["blue"]); ax.axvline(yv.mean(),ls="--",color=COLORS["coral"],label=f"Subset prevalence ({yv.mean():.1%})"); ax.set(xlabel="Average precision on next 2,000 rows",title="A declared subset comparison is a screening experiment—not the final benchmark"); ax.legend(); savefig("other-families.png"); return out


def search_experiment(ctx: dict) -> pd.DataFrame:
    X,y,folds=ctx["Xd"],ctx["yd"],ctx["folds"]; _,_,sparse,_=preprocessors(X)
    base=Pipeline([("prep",sparse),("model",LogisticRegression(max_iter=1000,solver="liblinear",random_state=SEED))])
    grids={"Grid search":[{"model__C":v} for v in [.01,.1,1,10]],"Randomized search":list(ParameterSampler({"model__C":np.logspace(-2,1,100)},n_iter=4,random_state=SEED))}
    rows=[]
    for method,configs in grids.items():
        start=time.perf_counter(); scored=[]
        for params in configs:
            vals=[]
            for tr,va in folds:
                m=clone(base).set_params(**params).fit(X.iloc[tr],y[tr]); vals.append(average_precision_score(y[va],m.predict_proba(X.iloc[va])[:,1]))
            scored.append((float(np.mean(vals)),params))
        elapsed=time.perf_counter()-start; best=max(scored,key=lambda z:z[0])
        rows.append({"method":method,"candidate_budget":4,"folds_per_candidate":3,"fits":12,"wall_clock_seconds":elapsed,"best_cv_average_precision":best[0],"best_params":json.dumps(best[1])})
    out=pd.DataFrame(rows); out.to_csv(ART/"search_comparison.csv",index=False)
    fig,axes=plt.subplots(1,2,figsize=(8,3.5)); axes[0].bar(out.method,out.best_cv_average_precision,color=[COLORS["blue"],COLORS["teal"]]); axes[0].set(ylabel="Best mean chronological CV AP",title="Same candidate budget"); axes[1].bar(out.method,out.wall_clock_seconds,color=[COLORS["blue"],COLORS["teal"]]); axes[1].set(ylabel="Measured wall-clock seconds",title="Actual runtime on this run"); [a.tick_params(axis="x",rotation=12) for a in axes]; savefig("search-budget.png"); return out


def calibration_thresholds(result: pd.DataFrame,predictions: dict,ctx: dict) -> pd.DataFrame:
    yh=ctx["yh"]; names=["Logistic regression",result[result.model!="Majority class"].sort_values("average_precision",ascending=False).iloc[0].model]
    fig,axes=plt.subplots(1,2,figsize=(9,4))
    for name in dict.fromkeys(names):
        p=predictions[name]; obs,mean=calibration_curve(yh,p,n_bins=10,strategy="quantile"); axes[0].plot(mean,obs,"o-",label=name)
    axes[0].plot([0,1],[0,1],ls="--",color=COLORS["gray"]); axes[0].set(xlabel="Mean predicted probability",ylabel="Observed fraction positive",title="Reliability on the chronological holdout"); axes[0].legend(fontsize=8)
    best=names[-1]; p=predictions[best]; rows=[]
    for t in np.linspace(.02,.80,80):
        pred=p>=t; tn,fp,fn,tp=confusion_matrix(yh,pred,labels=[0,1]).ravel()
        rows.append({"threshold":t,"selected":int(pred.sum()),"precision":precision_score(yh,pred,zero_division=0),"recall":recall_score(yh,pred,zero_division=0),"hypothetical_cost":int(fp+5*fn)})
    out=pd.DataFrame(rows); out.to_csv(ART/"threshold_sweep.csv",index=False)
    axes[1].plot(out.threshold,out.precision,label="Precision",color=COLORS["blue"]); axes[1].plot(out.threshold,out.recall,label="Recall",color=COLORS["coral"]); axes[1].set(xlabel="Decision threshold",ylabel="Metric",title=f"Thresholds change actions ({best})"); axes[1].legend(); savefig("calibration-thresholds.png")
    # Capacity rule evaluates exactly top 1,000 scores.
    top=np.argsort(-p)[:1000]; cap={"model":best,"capacity":1000,"positives_captured":int(yh[top].sum()),"precision_at_capacity":float(yh[top].mean()),"recall_at_capacity":float(yh[top].sum()/yh.sum()),"hypothetical_cost_definition":"FP + 5*FN"}
    (ART/"capacity_result.json").write_text(json.dumps(cap,indent=2)+"\n")
    return out


def bootstrap_uncertainty(result: pd.DataFrame,predictions: dict,ctx: dict) -> pd.DataFrame:
    best=result[result.model!="Majority class"].sort_values("average_precision",ascending=False).iloc[0].model; y=ctx["yh"]; p=predictions[best]; rng=np.random.default_rng(SEED); vals=[]
    for _ in range(500):
        idx=rng.integers(0,len(y),len(y)); vals.append([roc_auc_score(y[idx],p[idx]),average_precision_score(y[idx],p[idx])])
    arr=np.array(vals); out=pd.DataFrame({"metric":["ROC-AUC","Average precision"],"estimate":[roc_auc_score(y,p),average_precision_score(y,p)],"bootstrap_2.5%":np.quantile(arr,.025,axis=0),"bootstrap_97.5%":np.quantile(arr,.975,axis=0),"resamples":500}); out.to_csv(ART/"bootstrap_uncertainty.csv",index=False); return out


def main() -> None:
    ART.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True); style()
    if not DATA.exists(): raise FileNotFoundError("Run python scripts/download_data.py first")
    df=pd.read_csv(DATA,sep=";")
    result,predictions,ctx=primary_benchmark(df)
    plot_primary(result,predictions,ctx)
    leakage=leakage_experiment(df,ctx)
    synthetic=synthetic_mechanisms()
    objectives=objective_experiment()
    splits=tree_split_visual()
    boost=boosting_visual()
    families=other_families(ctx)
    search=search_experiment(ctx)
    thresholds=calibration_thresholds(result,predictions,ctx)
    uncertainty=bootstrap_uncertainty(result,predictions,ctx)
    summary={
        "best_primary_model_by_ap":result[result.model!="Majority class"].sort_values("average_precision",ascending=False).iloc[0].model,
        "primary_benchmark":result.to_dict(orient="records"),
        "prediction_moment_comparison":leakage.to_dict(orient="records"),
        "search":search.to_dict(orient="records"),
        "objective_comparison":objectives.to_dict(orient="records"),
        "synthetic":synthetic.to_dict(orient="records"),
        "other_families":families.to_dict(orient="records"),
        "uncertainty":uncertainty.to_dict(orient="records"),
    }
    (ART/"results.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))


if __name__=="__main__": main()
