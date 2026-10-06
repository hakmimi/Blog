---
title: "Gradient Boosting: לומדים מהטעויות של העץ הקודם"
description: "Boosting בונה הרבה עצים קטנים ברצף, וכל אחד מותאם למה שהאנסמבל עד כה עדיין מפספס. כותבים את הלולאה בכמה שורות, רואים איך קצב הלמידה מחליף מהירות באורך הריצה האפשרי, ומבינים למה קיימת עצירה מוקדמת."
series: "classification"
lang: "he"
order: 8
date: 2026-09-30
updated: 2026-10-04
keywords: ["gradient boosting", "קצב למידה", "עצירה מוקדמת", "xgboost", "lightgbm", "catboost"]
readingTime: "12 דקות קריאה"
figure: "ch08-boosting-lr.png"
---

מתאימים מודל boosting עם קצב למידה של 0.5, והציון שלו על שורות שלא ראה מגיע לשיא אחרי בערך 100 עצים ואז יורד. בינתיים הציון שלו על השורות שעליהן הותאם ממשיך לעלות. שום דבר באלגוריתם לא אומר לו לעצור. התצפית האחת הזו מסבירה את רוב העצות המעשיות על boosting.

<div class="callout">

**מטרה.** להבין את לולאת ה-boosting, מה קצב הלמידה עושה לה, ואיך בוחרים את מספר העצים בלי לנחש.

**תוכנית עבודה.** לכתוב gradient boosting עם log loss בכמה שורות. להריץ אותו בשלושה קצבי למידה ולדרג כל שלב על שורות אימות פנימיות. ואז לתת לעצירה מוקדמת לבחור את מספר העצים, ולמקם את הספריות בעלות השם בהקשר.

</div>

## האלגוריתם במילים פשוטות

יערות אקראיים מחשבים ממוצע של הרבה עצים עמוקים ובלתי תלויים. Boosting עושה את ההפך: הוא מוסיף הרבה עצים קטנים בזה אחר זה, וכל עץ חדש מאומן לתקן את מה שהאנסמבל עד כה עדיין מפספס.

1. מתחילים בציון קבוע: לוג-הסיכויים של השיעור הכללי.
2. לכל רשומה מחשבים את ה**שארית** (residual): התוצאה פחות ההסתברות החזויה הנוכחית. עבור log loss זה בדיוק מינוס הגרדיינט של ההפסד לפי הציון הנוכחי.
3. מתאימים עץ קטן שחוזה את השאריות האלה.
4. מוסיפים את הפלט של העץ, מוכפל ב**קצב למידה** קטן, לציון המצטבר.
5. חוזרים.

החיזוי הוא `sigmoid(F₀ + η·tree₁ + η·tree₂ + …)`. כל צעד הוא צעד של ירידה במורד הגרדיינט, שנעשה במרחב של פונקציות ולא במרחב של משקלים. כמו קודם, מתאימים על 75% משורות הפיתוח ומדרגים על ה-25% האחרים.

**מימוש.**

```python
import numpy as np
import pandas as pd
from sklearn.compose import make_column_transformer
from sklearn.metrics import average_precision_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeRegressor

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns=["duration", "campaign"])
dev, _ = train_test_split(np.arange(len(X)), test_size=0.2, stratify=y, random_state=42)
dev = np.sort(dev)
fit, val = train_test_split(dev, test_size=0.25, stratify=y[dev], random_state=42)
cat = [c for c in X.columns if X[c].dtype == object]
prep = make_column_transformer((OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat), remainder="passthrough")
A, B = prep.fit_transform(X.iloc[fit]), prep.transform(X.iloc[val])
yf, yv = y[fit], y[val]
sigmoid = lambda z: 1 / (1 + np.exp(-z))

def boost(lr, stages):
    start = np.log(yf.mean() / (1 - yf.mean()))                     # stage 0: the base rate
    F_fit, F_val = np.full(len(A), start), np.full(len(B), start)
    curve = {}
    for m in range(1, stages + 1):
        residual = yf - sigmoid(F_fit)                              # negative gradient of log loss
        tree = DecisionTreeRegressor(max_depth=3, min_samples_leaf=20).fit(A, residual)
        F_fit += lr * tree.predict(A)
        F_val += lr * tree.predict(B)
        if m in (1, 10, 50, 100, 300):
            curve[m] = (average_precision_score(yv, F_val), average_precision_score(yf, F_fit))
    return curve

for lr in (0.5, 0.1):
    print(f"learning rate {lr}")
    for m, (v, f) in boost(lr, 300).items():
        print(f"  {m:>4} trees: validation AP {v:.3f}   fitted rows AP {f:.3f}")
```

**תוצאה.**

```output
learning rate 0.5
     1 trees: validation AP 0.374   fitted rows AP 0.374
    10 trees: validation AP 0.408   fitted rows AP 0.409
    50 trees: validation AP 0.458   fitted rows AP 0.472
   100 trees: validation AP 0.461   fitted rows AP 0.493
   300 trees: validation AP 0.454   fitted rows AP 0.527
learning rate 0.1
     1 trees: validation AP 0.374   fitted rows AP 0.374
    10 trees: validation AP 0.378   fitted rows AP 0.382
    50 trees: validation AP 0.413   fitted rows AP 0.417
   100 trees: validation AP 0.452   fitted rows AP 0.451
   300 trees: validation AP 0.457   fitted rows AP 0.476
```

הלולאה הזו היא gradient boosting. ספריות אמיתיות מוסיפות צעד מסדר שני כדי לקבוע את ערכי העלים, רגולריזציה ומציאת פיצולים מהירה בהרבה, אבל השלד הוא זה.

## קצב למידה, גלוי לעין

הטבלה מריצה את אותה לולאה ל-1,000 שלבים בשלושה קצבי למידה (AP באימות; הקטע למעלה מראה את 300 השלבים הראשונים לשניים מהם).

| עצים | 0.5 | 0.1 | 0.02 |
|---|---|---|---|
| 1 | 0.374 | 0.374 | 0.374 |
| 10 | 0.408 | 0.378 | 0.374 |
| 25 | 0.456 | 0.391 | 0.376 |
| 50 | 0.458 | 0.413 | 0.378 |
| 100 | 0.461 | 0.452 | 0.381 |
| 200 | 0.456 | 0.458 | 0.409 |
| 300 | 0.454 | 0.457 | 0.421 |
| 500 | 0.450 | 0.460 | 0.453 |
| 1,000 | 0.447 | 0.456 | 0.458 |

![דיוק ממוצע באימות מול שלבי boosting לשלושה קצבי למידה.](/series/classification/figures/ch08-boosting-lr.png)
*איור 1. קצב למידה גדול לומד מהר ואז מתאים יתר על המידה. קטן איטי יותר ועדיין משתפר ב-1,000 עצים.*

מה המספרים אומרים:

- **צעדים גדולים מהירים, ואז מסוכנים.** בקצב למידה של 0.5 ה-AP באימות הוא 0.461 ב-100 עצים ו-0.447 ב-1,000, בעוד ה-AP על שורות ההתאמה מטפס מ-0.493 ל-0.586: המודל מתאר יותר ויותר רעש.
- **צעדים קטנים צריכים יותר עצים, והחישוב קובע אם מגיעים.** קצב של 0.1 מגיע לשיא ב-500 עצים (0.460). ב-0.02 הציון עדיין עולה ב-1,000 עצים (0.458) ורחוק מאחור ב-300 (0.421). קצבים קטנים לרוב מסתיימים דומה או מעט טוב יותר, אבל רק אם אפשר להרשות לעצמכם את העצים.
- **קצב הלמידה ומספר העצים משפיעים זה על זה.** חצי מהקצב מכפיל בערך את העצים שצריך כדי להגיע לאותו מקום. זה לא הופך חיפוש משותף לפסול, אבל הופך אותו לבזבזני, ובגלל זה הנוהל הרגיל הוא לקבוע קצב למידה קטן ולבחור את מספר העצים בעצירה מוקדמת.
- **הציונים הטובים ביותר של שלוש ההרצות נבדלים בפחות מ-0.003**, ולכן בנתונים האלה בחירת קצב הלמידה משנה בעיקר כמה עצים צריך וכמה בזהירות צריך לעצור.

## עצירה מוקדמת

במקום לנחש מספר עצים, מחזיקים בצד פרוסה מנתוני האימון, מדרגים אותה אחרי כל עץ, ועוצרים כשהיא לא השתפרה במשך מספר סבבים קבוע. `HistGradientBoostingClassifier` של scikit-learn כולל את זה מובנה, יחד עם טיפול טבעי בעמודות קטגוריאליות וחיפוש פיצולים מהיר מבוסס היסטוגרמות.

**מימוש.**

```python
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import log_loss

cats = {c: sorted(X.iloc[fit][c].unique()) for c in cat}
def as_category(rows):
    Z = X.iloc[rows].copy()
    for c in cat:
        Z[c] = pd.Categorical(Z[c], categories=cats[c])
    return Z

Zf, Zv = as_category(fit), as_category(val)
for lr in (0.3, 0.1, 0.03):
    h = HistGradientBoostingClassifier(learning_rate=lr, max_iter=2000, early_stopping=True, validation_fraction=0.15,
                                       n_iter_no_change=30, categorical_features="from_dtype", random_state=42).fit(Zf, yf)
    q = h.predict_proba(Zv)[:, 1]
    print(f"learning rate {lr}: stopped at {h.n_iter_:>3} trees, validation AP {average_precision_score(yv, q):.3f}, log loss {log_loss(yv, q):.3f}")
```

**תוצאה.**

```output
learning rate 0.3: stopped at  36 trees, validation AP 0.440, log loss 0.283
learning rate 0.1: stopped at  61 trees, validation AP 0.454, log loss 0.275
learning rate 0.03: stopped at 123 trees, validation AP 0.454, log loss 0.274
```

**מה זה אומר.** איפשרנו 2,000 עצים והמודלים נעצרו בין 36 לכ-120. שני הקצבים הקטנים מסתיימים כמעט באותו AP וב-log loss באימות; הגדול ביותר גרוע בשניהם. פרוסת האימות חייבת להיראות כמו העתיד שאכפת לכם ממנו: פרוסה אקראית של 15% מתאימה לחלוקה אקראית, אבל אם השאלה היא על רשומות *מאוחרות* (חלק 16), מאמתים על נתוני האימון העדכניים ביותר, כי פרוסה אקראית מהעבר ממשיכה לתגמל עצים נוספים הרבה אחרי שהמודל הפסיק להכליל קדימה בזמן.

## הספריות בעלות השם

כל מה שלמעלה הוא הליבה. XGBoost, LightGBM ו-CatBoost הן גרסאות הנדסיות שלה, והרבה מההבדלים ניתנים להגדרה, ולכן קראו את הטבלה כברירות מחדל לגרסאות שבהן השתמשנו (XGBoost 3.4.1, LightGBM 4.7.0, CatBoost 1.2.10, scikit-learn 1.8.0).

| | גידול עץ כברירת מחדל | עמודות קטגוריאליות | ידוע בזכות |
|---|---|---|---|
| XGBoost | שכבה אחרי שכבה, מוגבל בעומק | תמיכה טבעית זמינה (`enable_categorical`) | פונקציית מטרה מוסדרת, גרדיינטים מסדר שני, אקוסיסטם גדול מאוד |
| LightGBM | עלה אחרי עלה (העלה הטוב ביותר קודם), נשלט על ידי `num_leaves` | תמיכה טבעית | מהירות על נתונים גדולים |
| CatBoost | עצים סימטריים ("oblivious") | טבעית, עם סטטיסטיקות מטרה מסודרות | ברירות מחדל חזקות לנתונים עתירי קטגוריות |
| scikit-learn `HistGradientBoosting` | עלה אחרי עלה | תמיכה טבעית | בלי תלות נוספת, עצירה מוקדמת מובנית |

האם אחד מההבדלים האלה חשוב ל*בעיה הזו* היא שאלה אמפירית, שנענית תחת פרוטוקול אחד בחלק 12.

## Boosting ו-bagging זה לצד זה

| | יער אקראי (חלק 7) | Gradient boosting |
|---|---|---|
| עצים | עמוקים, בלתי תלויים, ממוצעים | רדודים, ברצף, מסוכמים |
| מקטין בעיקר | שונות | הטיה, וגם שונות בקצבי למידה קטנים |
| רגישות להגדרות | בדרך כלל נמוכה | בינונית: קצב למידה, גודל עץ, רגולריזציה, עצירה |
| יותר עצים | כמעט אף פעם לא פוגע, מייצב | יכול להתאים יתר על המידה, ולכן עוצרים לפי נתוני אימות |
| הסתברויות | תלויות בגודל העלה | סבירות כשמאמנים על log loss, ועדיין כדאי לבדוק (חלק 11) |

## ניתוח ומסקנה: מה למדנו

- **הלולאה קצרה.** שארית, עץ קטן, צעד קטן, חוזרים. כל השאר בספריות הוא מהירות, רגולריזציה ונוחות.
- **שום דבר ב-boosting לא אומר לעצור.** קצב למידה גדול מתאים יתר על המידה בתוך מאה עצים בנתונים האלה. בוחרים את מספר העצים על נתוני אימות.
- **צעדים קטנים אינם טובים יותר אוטומטית.** הם חלקים יותר ולרוב טובים לפחות באותה מידה, אבל תחת תקציב סופי קצב למידה קטן אולי פשוט לא רץ מספיק זמן.
- **עצירה מוקדמת חייבת לאמת את הדבר הנכון.** משתמשים בשורות אימות אקראיות לחלוקה אקראית ובשורות האחרונות לחלוקה מסודרת בזמן.

*לקריאה נוספת.* Friedman (2001), [Greedy function approximation: a gradient boosting machine](https://doi.org/10.1214/aos/1013203451); Chen ו-Guestrin (2016), [XGBoost](https://doi.org/10.1145/2939672.2939785); Ke ואחרים (2017), LightGBM, NeurIPS; Prokhorenkova ואחרים (2018), [CatBoost](https://arxiv.org/abs/1706.09516).

[חלק 9](/he/series/classification/09-other-classification-families/) עובר על המשפחות שנותרו, שכנים קרובים, מכונות וקטורים תומכים ורשתות עצביות, שדורשות טיפול שונה מאוד באותם נתונים.
