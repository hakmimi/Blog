---
title: "עצי החלטה: קלים לקריאה, קלים להתאמת יתר"
description: "עץ שגדל עד הסוף מקבל 0.99 על השורות שעליהן הותאם ו-0.19 על שורות שלא ראה. מחשבים פיצול ביד, צופים בפער נפתח כשהעץ גדל, וקוראים עץ קטן כמו תרשים זרימה."
series: "classification"
lang: "he"
order: 6
date: 2026-09-30
updated: 2026-10-04
keywords: ["עצי החלטה", "אי-טהירות ג'יני", "התאמת יתר", "הצלבה", "scikit-learn"]
readingTime: "12 דקות קריאה"
figure: "ch06-tree-overfit.png"
---

מגדלים עץ החלטה עד שאי אפשר לפצל אותו יותר, והוא מקבל דיוק ממוצע של @@v:trees_sweeps.csv|setting=max_depth|value=unlimited|train_ap|.2f@@ על השורות שעליהן הותאם. שואלים אותו על שורות שלא ראה, בהצלבה, והציון הוא @@v:trees_sweeps.csv|setting=max_depth|value=unlimited|cv_ap_mean|.2f@@. עץ יכול לשנן. החלק הזה מראה איך רואים את זה במספרים, איך עוצרים את זה, ולמה עץ קטן טוב.

<div class="callout">

**מטרה.** להבין איך עץ בוחר פיצולים, איך צריך לשלוט במורכבות שלו, ומה הוא יכול ומה הוא לא יכול לספר לכם.

**תוכנית עבודה.** לחשב פיצול אחד ביד עם אי-טהירות ג'יני. לגדל עצים בעומק גדל ולהשוות ציונים על שורות ההתאמה ועל שורות שלא נראו. לשלוט במורכבות עם גודל העלה המינימלי. להדפיס עץ קטן ולקרוא אותו.

</div>

## איך עץ בוחר פיצול

עץ גדל בחמדנות. בכל צומת הוא בוחן כל תכונה וכל סף מועמד, בוחר את הפיצול שהופך את שתי קבוצות הצאצאים ל"טהורות" ביותר, וחוזר על כך בתוך כל צאצא. הטוהר נמדד כאן ב**אי-טהירות ג'יני** (Gini impurity): בצומת שבו חלק *p* מהרשומות נרשמים, `gini = 2·p·(1−p)`. היא 0 לצומת עם מחלקה אחת ו-0.5 לתערובת של 50/50. הערך של פיצול הוא אי-הטהירות שהוא מסיר, משוקלל בגודל כל צאצא.

**מימוש.** מחשבים את זה בעצמנו על שורות הפיתוח.

```python
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns=["duration", "campaign"])
dev, _ = train_test_split(np.arange(len(X)), test_size=0.2, stratify=y, random_state=42)
dev = np.sort(dev)
Xd, yd = X.iloc[dev], y[dev]

gini = lambda labels: 2 * labels.mean() * (1 - labels.mean())

def gain(feature, threshold):
    left = yd[Xd[feature].to_numpy() <= threshold]
    right = yd[Xd[feature].to_numpy() > threshold]
    child = (len(left) * gini(left) + len(right) * gini(right)) / len(yd)
    return gini(yd) - child

print(f"root impurity: {gini(yd):.4f}")
for feature, t in [("euribor3m", 1.0), ("euribor3m", 5.0), ("pdays", 16.5), ("nr.employed", 5087.65)]:
    print(f"split {feature} <= {t}: impurity removed {gain(feature, t):.4f}")
```

**תוצאה.**

```output
(filled in by the build)
```

**מה זה אומר.** אי-הטהירות בשורש היא 0.1999, מחלקם של המנויים, 11.3%. פיצול לפי `nr.employed` ב-5,087.65 מסיר הכי הרבה מבין ארבעת המועמדים האלה, חיתוך של הריבית ב-5.0 מסיר כמעט כלום, וחיתוך ב-1.0 מסיר כמות שימושית. אלגוריתם להתאמת עץ הוא החישוב הזה שחוזר על עצמו לכל תכונה ולכל סף בכל צומת. scikit-learn עושה את זה בקוד מקומפל, אבל אין כאן שום דבר מסתורי יותר.

## אותו עץ בעומקים שונים

השאלה שחשובה היא מתי לעצור. משנים את `max_depth` ומדרגים דיוק ממוצע פעמיים: על השורות שעליהן העץ הותאם, ובהצלבה של 5 קיפולים על שורות הפיתוח (הציון של כל קיפול בא משורות שהעץ שלו לא ראה).

**מימוש.**

```python
from sklearn.compose import make_column_transformer
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics import average_precision_score
from sklearn.tree import DecisionTreeClassifier

cat = [c for c in X.columns if X[c].dtype == object]
prep = make_column_transformer((OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat), remainder="passthrough")
cv = StratifiedKFold(5, shuffle=True, random_state=42)

print(f"{'max_depth':>9}{'leaves':>8}{'fitted rows':>13}{'held-out (CV)':>15}")
for depth in (2, 3, 5, 8, 12, None):
    tree = make_pipeline(prep, DecisionTreeClassifier(max_depth=depth, random_state=42)).fit(Xd, yd)
    fitted = average_precision_score(yd, tree.predict_proba(Xd)[:, 1])
    held_out = cross_val_score(tree, Xd, yd, scoring="average_precision", cv=cv).mean()
    print(f"{str(depth):>9}{tree[-1].get_n_leaves():>8}{fitted:>13.3f}{held_out:>15.3f}")
```

**תוצאה.**

```output
(filled in by the build)
```

![הדיוק הממוצע על שורות ההתאמה ממשיך לעלות עם העומק, בעוד הדיוק הממוצע בהצלבה מגיע לשיא ואז יורד.](/series/classification/figures/ch06-tree-overfit.png)
*איור 1. הפער בין הציונים על שורות ההתאמה לשורות שלא נראו נפתח כשהעץ גדל.*

**מה זה אומר.** עצים רדודים (עומק 2 ו-3) מקבלים בערך אותו ציון בשני המקרים, ולכן הם פשוטים מדי. הציון על שורות שלא נראו מגיע לשיא ליד עומק 5, בעוד הציון על שורות ההתאמה ממשיך לטפס ל-@@v:trees_sweeps.csv|setting=max_depth|value=unlimited|train_ap|.3f@@ בעץ ללא הגבלה, והציון על שורות שלא נראו יורד ל-@@v:trees_sweeps.csv|setting=max_depth|value=unlimited|cv_ap_mean|.3f@@ (דירוג אקראי מקבל @@j:trees_notes.json|development_prevalence|.3f@@). לעץ הזה יש @@v:trees_sweeps.csv|setting=max_depth|value=unlimited|leaves|d@@ עלים על כ-26,000 רשומות אימון, ולכן בהרבה עלים יש קומץ רשומות. **ציון על השורות שעליהן מודל גמיש הותאם אומר מעט על שורות חדשות.**

## חוגה טובה יותר: העלה הקטן ביותר

`max_depth` מגביל כל ענף באותה מידה. **גודל העלה המינימלי** (`min_samples_leaf`) ממוקד יותר: פיצול מותר רק אם שני הצאצאים שומרים לפחות כך וכך רשומות, ולכן ענף יכול להעמיק איפה שיש נתונים, ועלה של שלוש רשומות לא יכול להיווצר.

@@table:trees_sweeps.csv|where=setting==min_samples_leaf|cols=value,leaves,train_ap,cv_ap_mean,cv_ap_sd|fmt=leaves:d|rename=value:min_samples_leaf,leaves:עלים,train_ap:שורות ההתאמה,cv_ap_mean:שורות שלא נראו (הצלבה),cv_ap_sd:סטיית תקן בין קיפולים@@

בנתונים האלה, גדלי עלה של 50 עד 100 נותנים את הציונים הטובים ביותר על שורות שלא נראו מבין מה שניסינו (@@v:trees_sweeps.csv|setting=min_samples_leaf|value=50|cv_ap_mean|.3f@@ ו-@@v:trees_sweeps.csv|setting=min_samples_leaf|value=100|cv_ap_mean|.3f@@, לעומת @@v:trees_sweeps.csv|setting=max_depth|value=5|cv_ap_mean|.3f@@ עבור מגבלת העומק הטובה ביותר); עלים של 1 או 5 מתאימים יתר על המידה ועלים של 500 מתאימים פחות מדי. זה ממצא על מערך הנתונים הזה ועל גודלו, לא כלל אוניברסלי: עם פי עשרה נתונים העלה הטוב ביותר כנראה גדול יותר, ועלים קטנים יותר יכולים להיות הגיוניים בתוך אנסמבל (חלק 7). עלים גדולים יותר גם הופכים כל ערך עלה לחלק מרשומות רבות, וזה נותן דירוג עדין יותר.

## קריאה של עץ קטן

היתרון הגדול של עץ קטן הוא שהוא מתעד את עצמו. הנה עץ בעומק 3 ועם עלים של לפחות 50 רשומות, שהותאם על שורות הפיתוח. כל עלה מציג ספירות `[no, yes]`.

**מימוש.**

```python
from sklearn.tree import export_text

small = make_pipeline(prep, DecisionTreeClassifier(max_depth=3, min_samples_leaf=50, random_state=42)).fit(Xd, yd)
print(export_text(small[-1], feature_names=list(small[0].get_feature_names_out()), show_weights=True))
```

**תוצאה.**

```output
(filled in by the build)
```

**מה זה אומר.** עקבו אחרי הענף הראשון: `nr.employed` ב-5,087.65 או מתחת, `pdays` עד 16.5 (נוצר קשר בקמפיין קודם בתוך 16 ימים), ולא ביום שני. העלה הזה מחזיק 205 רשומות "no" ו-583 רשומות "yes" (74%), הקטע הטוב ביותר, ומודל לינארי היה צריך אינטראקציה שנבנתה ביד כדי לבטא אותו. שימו לב מה `nr.employed` עושה בשורש: היא יורדת בהתמדה לאורך הקובץ (מתאם דרגות עם מיקום השורה @@j:trees_notes.json|spearman_row_position_vs_nr_employed|.2f@@), ולכן פיצול לפיה מפריד בין רשומות מוקדמות למאוחרות ומשמש תחליף ל*זמן*. חלק 16 מראה מה זה עושה למודל שמתבקש לחזות רשומות מאוחרות.

## ניתוח ומסקנה: מה למדנו

- **ציונים על שורות ההתאמה אינם ראיה להכללה.** העץ ללא הגבלה הגיע ל-@@v:trees_sweeps.csv|setting=max_depth|value=unlimited|train_ap|.2f@@ על השורות ששינן ול-@@v:trees_sweeps.csv|setting=max_depth|value=unlimited|cv_ap_mean|.2f@@ על שורות שלא נראו.
- **מורכבות צריכה חוגה.** עומק 5 ועלה מינימלי של 50 עד 100 הן ההגדרות הטובות ביותר שנבדקו כאן, וחוגת גודל העלה הצליחה מעט יותר.
- **עץ קטן הוא סיכום קריא**, אבל עץ אחד הוא מודל עם שונות גבוהה: שינוי הרשומות שהוא רואה יכול לשנות את הפיצולים העליונים שלו, וזה מה ש-bagging מנצל בחלק 7.
- **עץ יכול להשתמש בעמודה כשעון.** התייחסו לפיצולים חזקים לפי `nr.employed` או לפי הריבית כאל דגל לבדיקה, לא כהתנהגות של לקוחות.

*לקריאה נוספת.* Breiman, Friedman, Olshen ו-Stone (1984), *Classification and Regression Trees*.

[חלק 7](/he/series/classification/07-bagging-random-forests/) ממשיך מכאן: אם עץ אחד לא יציב, מה קורה כשמחשבים ממוצע של הרבה מהם?
